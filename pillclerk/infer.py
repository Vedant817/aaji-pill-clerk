"""Line → MedLine JSON. PARSER_BACKEND=tinker uses hosted sampling (no local GGUF)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pillclerk import config
from pillclerk.copy_explicit import copy_explicit, stub_from_line
from pillclerk.privacy import strip_pii
from pillclerk.schema import SYSTEM_PROMPT, MedLine
from pillclerk.validate import extra_rules

ParseFn = Callable[[str], MedLine | None]

JSON_ONLY = (
    " Reply with one JSON object only. No markdown fences, no prose. "
    "form is lowercase tab|cap|syrup|drops|inhaler|injection|cream|sachet|other (never TAB). "
    "kind is daily|prn|taper (never regular). "
    "food is before|after|with|empty_stomach|any (never AFTER FOOD). "
    "dose is an object {morning, afternoon, night, unit}, never a string like \"1-0-1\". "
    "Missing fields are null and listed in needs_check."
)
JSON_SCHEMA_HINTS = (
    " dose.unit is tab|cap|ml|drop|puff|unit|sachet|apply. "
    "strength is a string (for example \"40 mg\"), never an object. "
    "taper is a list of {dose:{morning,afternoon,night,unit}, days}."
)


@dataclass
class ParseOutcome:
    pred: MedLine | None
    raw: str | None = None
    error: str | None = None
    accepted_config: dict = field(default_factory=dict)
    finish_reason: str | None = None

# Three gold pairs from train.jsonl, held out of synth_test and handwritten_realistic.
FEW_SHOT: list[tuple[str, MedLine]] = [
    (
        "5. Tab Pantoprazole 40mg subah ek raat ko ek khane ke baad 3 din",
        MedLine(
            drug="Pantoprazole",
            strength="40 mg",
            form="tab",
            kind="daily",
            dose={"morning": 1.0, "afternoon": 0.0, "night": 1.0, "unit": "tab"},
            food="after",
            duration_days=3,
        ),
    ),
    (
        "TAB. Sucral 1 g SOS / PRN max 2/d x 7 DAYS",
        MedLine(
            drug="Sucral",
            strength="1 g",
            form="tab",
            kind="prn",
            food="any",
            duration_days=7,
            prn_max_per_day=2,
        ),
    ),
    (
        "Tab Lasix 40 mg subah ek raat ko ek khali pet 7 din",
        MedLine(
            drug="Lasix",
            strength="40 mg",
            form="tab",
            kind="daily",
            dose={"morning": 1.0, "afternoon": 0.0, "night": 1.0, "unit": "tab"},
            food="empty_stomach",
            duration_days=7,
        ),
    ),
]

# Extra Gemma JSON-mode shots from train.jsonl. Lines are disjoint from every eval set
# (eval.overlap.vs_eval). Drugs are not in eval_drug_names().
GEMINI_EXTRA_FEW_SHOT: list[tuple[str, MedLine]] = [
    (
        "TAB. Metrogyl 400 mg 1-0-1 x 5d then 0-0-1 x 5d BEFORE FOOD",
        MedLine(
            drug="Metrogyl",
            strength="400 mg",
            form="tab",
            kind="taper",
            dose=None,
            taper=[
                {"dose": {"morning": 1.0, "afternoon": 0.0, "night": 1.0, "unit": "tab"}, "days": 5},
                {"dose": {"morning": 0.0, "afternoon": 0.0, "night": 1.0, "unit": "tab"}, "days": 5},
            ],
            food="before",
            duration_days=10,
        ),
    ),
    (
        "DROPS Timolol 0.5 % 0-0-2 रात दो khane ke baad x5d",
        MedLine(
            drug="Timolol",
            strength="0.5 %",
            form="drops",
            kind="daily",
            dose={"morning": 0.0, "afternoon": 0.0, "night": 2.0, "unit": "drop"},
            food="after",
            duration_days=5,
        ),
    ),
    (
        "Inj Huminsulin 40 IU/ml 10-10-10 WF x5d",
        MedLine(
            drug="Huminsulin",
            strength="40 IU/ml",
            form="injection",
            kind="daily",
            dose={"morning": 10.0, "afternoon": 10.0, "night": 10.0, "unit": "unit"},
            food="with",
            duration_days=5,
        ),
    ),
]


def chat_messages(line: str, *, few_shot: bool = False) -> list[dict[str, str]]:
    """FT2 template is SYSTEM_PROMPT + user line. B0-fair adds JSON-only + 3 shots."""
    system = SYSTEM_PROMPT + (JSON_ONLY if few_shot else "")
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    if few_shot:
        for user, gold in FEW_SHOT:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": gold.model_dump_json()})
    messages.append({"role": "user", "content": line})
    return messages


def gemini_teacher_messages(line: str, *, json_mode: bool = False) -> list[dict[str, str]]:
    """Single user turn: Gemma 4 often ignores systemInstruction and few-shot chat."""
    shots = FEW_SHOT + (GEMINI_EXTRA_FEW_SHOT if json_mode else [])
    examples = "\n\n".join(
        f"Line: {user}\nJSON: {gold.model_dump_json()}" for user, gold in shots
    )
    hints = JSON_ONLY + (JSON_SCHEMA_HINTS if json_mode else "")
    user = (
        f"{SYSTEM_PROMPT}{hints}\n\n"
        f"Examples:\n{examples}\n\n"
        f"Line: {line}\n"
        "JSON:"
    )
    return [{"role": "user", "content": user}]


def classify_gemini_failure(text: str, finish_reason: str | None, pred: MedLine | None) -> str | None:
    if pred is not None:
        return None
    reason = (finish_reason or "").upper()
    if reason in {"MAX_TOKENS", "LENGTH"}:
        return "truncated"
    blob = _extract_json(text or "")
    if not text or "{" not in text or not blob.startswith("{"):
        return "no_json"
    return "schema"


def _extract_json(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    text = text.replace("<think>", "").replace("</think>", "")
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_ollama(line: str, model: str | None = None) -> MedLine | None:
    import ollama

    r = ollama.chat(
        model=model or config.OLLAMA_PARSER_MODEL,
        think=False,
        format=MedLine.model_json_schema(),
        options={"temperature": 0},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": line},
        ],
    )
    try:
        med = extra_rules(MedLine.model_validate_json(r.message.content))
        return extra_rules(copy_explicit(med, line))
    except Exception:
        return extra_rules(copy_explicit(stub_from_line(line), line))


def as_token_ids(ids: Any) -> list[int]:
    if isinstance(ids, dict):
        ids = ids.get("input_ids", ids)
    if hasattr(ids, "input_ids"):
        ids = ids.input_ids
    if ids and isinstance(ids, (list, tuple)) and isinstance(ids[0], (list, tuple)):
        ids = ids[0]
    return [int(x) for x in list(ids)]


def _qwen_prompt(tokenizer: Any, line: str, *, few_shot: bool = False) -> list[int]:
    messages = chat_messages(line, few_shot=few_shot)
    kwargs: dict[str, Any] = {"tokenize": True, "add_generation_prompt": True}
    try:
        ids = tokenizer.apply_chat_template(messages, enable_thinking=False, **kwargs)
    except TypeError:
        ids = tokenizer.apply_chat_template(messages, **kwargs)
    return as_token_ids(ids)


def make_tinker_parser(
    model_path: str | None = None,
    base_model: str = config.BASE_MODEL,
    *,
    few_shot: bool = False,
) -> ParseFn:
    """model_path=tinker://... for the fine-tune, None for the base model (B0 / B0-fair)."""
    import tinker

    svc = tinker.ServiceClient()
    if model_path:
        sc = svc.create_sampling_client(model_path=model_path)
    else:
        sc = svc.create_sampling_client(base_model=base_model)
    tokenizer = sc.get_tokenizer()
    params = tinker.SamplingParams(max_tokens=400, temperature=0.0)

    def parse(line: str) -> MedLine | None:
        clean, _stripped = strip_pii(line)
        prompt_tokens = _qwen_prompt(tokenizer, clean, few_shot=few_shot)
        model_input = tinker.ModelInput.from_ints(prompt_tokens)
        res = sc.sample(prompt=model_input, num_samples=1, sampling_params=params).result()
        text = tokenizer.decode(res.sequences[0].tokens)
        try:
            med = extra_rules(MedLine.model_validate_json(_extract_json(text)))
            return extra_rules(copy_explicit(med, clean))
        except Exception:
            return extra_rules(copy_explicit(stub_from_line(clean), clean))

    return parse


def parse_medline_blob(text: str) -> MedLine | None:
    """Pick the first JSON object in text that validates as MedLine."""
    blob = _extract_json(text)
    try:
        return extra_rules(MedLine.model_validate_json(blob))
    except Exception:
        pass
    decoder = json.JSONDecoder()
    i = 0
    while i < len(text):
        start = text.find("{", i)
        if start == -1:
            return None
        try:
            obj, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            i = start + 1
            continue
        if isinstance(obj, dict):
            try:
                return extra_rules(MedLine.model_validate(obj))
            except Exception:
                i = end
                continue
        i = end
    return None


def parse_gemini_text(text: str, line: str) -> MedLine | None:
    med = parse_medline_blob(text)
    if med is None:
        return None
    return extra_rules(copy_explicit(med, line))


def make_gemini_parser(set_path: str, *, json_mode: bool = False) -> Callable[[str], ParseOutcome]:
    """Gemma 4 31B teacher. Text-only, allowlisted eval sets, payload log."""
    from pillclerk.privacy import assert_gemini_eval_set, log_sent_payload
    from pillclerk.render import GeminiBackend

    allowed = str(assert_gemini_eval_set(Path(set_path)))
    backend = GeminiBackend()
    model = backend.model
    system = "gemma31_json" if json_mode else "gemma31"

    def parse(line: str) -> ParseOutcome:
        clean, stripped = strip_pii(line)
        messages = gemini_teacher_messages(clean, json_mode=json_mode)
        log_sent_payload(
            system=system,
            set_path=allowed,
            model=model,
            line=clean,
            stripped=stripped,
            messages=messages,
        )
        result = backend.complete_detailed(
            messages, temperature=0.0, max_tokens=1024, json_mode=json_mode
        )
        if result.error:
            return ParseOutcome(
                pred=None,
                raw=result.text,
                error=result.error,
                accepted_config=result.accepted_config,
                finish_reason=result.finish_reason,
            )
        pred = parse_gemini_text(result.text, clean)
        return ParseOutcome(
            pred=pred,
            raw=result.text,
            error=classify_gemini_failure(result.text, result.finish_reason, pred),
            accepted_config=result.accepted_config,
            finish_reason=result.finish_reason,
        )

    return parse


def get_parser() -> ParseFn:
    backend = config.parser_backend()
    if backend == "ollama":
        return lambda line: parse_ollama(line)
    path = config._get("PILLCLERK_TINKER_PATH") or None
    return make_tinker_parser(path)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Parse one prescription line via Tinker.")
    ap.add_argument("--line", required=True)
    ap.add_argument("--path", default="", help="tinker:// sampler path; default is PILLCLERK_TINKER_PATH")
    args = ap.parse_args()
    path = args.path.strip() or config._get("PILLCLERK_TINKER_PATH") or None
    pred = make_tinker_parser(path)(args.line)
    if pred is None:
        print("PARSE_FAILED")
        raise SystemExit(1)
    print(pred.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
