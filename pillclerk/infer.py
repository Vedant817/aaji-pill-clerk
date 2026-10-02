"""Line → MedLine JSON. PARSER_BACKEND=tinker uses hosted sampling (no local GGUF)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from pillclerk import config
from pillclerk.copy_explicit import copy_explicit
from pillclerk.schema import SYSTEM_PROMPT, MedLine
from pillclerk.validate import extra_rules

ParseFn = Callable[[str], MedLine | None]


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
        return None


def as_token_ids(ids: Any) -> list[int]:
    if isinstance(ids, dict):
        ids = ids.get("input_ids", ids)
    if hasattr(ids, "input_ids"):
        ids = ids.input_ids
    if ids and isinstance(ids, (list, tuple)) and isinstance(ids[0], (list, tuple)):
        ids = ids[0]
    return [int(x) for x in list(ids)]


def _qwen_prompt(tokenizer: Any, line: str) -> list[int]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": line},
    ]
    kwargs: dict[str, Any] = {"tokenize": True, "add_generation_prompt": True}
    try:
        ids = tokenizer.apply_chat_template(messages, enable_thinking=False, **kwargs)
    except TypeError:
        ids = tokenizer.apply_chat_template(messages, **kwargs)
    return as_token_ids(ids)


def make_tinker_parser(
    model_path: str | None = None,
    base_model: str = config.BASE_MODEL,
) -> ParseFn:
    """model_path=tinker://... for the fine-tune, None for the base model (B0)."""
    import tinker

    svc = tinker.ServiceClient()
    if model_path:
        sc = svc.create_sampling_client(model_path=model_path)
    else:
        sc = svc.create_sampling_client(base_model=base_model)
    tokenizer = sc.get_tokenizer()
    params = tinker.SamplingParams(max_tokens=400, temperature=0.0)

    def parse(line: str) -> MedLine | None:
        prompt_tokens = _qwen_prompt(tokenizer, line)
        model_input = tinker.ModelInput.from_ints(prompt_tokens)
        res = sc.sample(prompt=model_input, num_samples=1, sampling_params=params).result()
        text = tokenizer.decode(res.sequences[0].tokens)
        try:
            med = extra_rules(MedLine.model_validate_json(_extract_json(text)))
            return extra_rules(copy_explicit(med, line))
        except Exception:
            return None

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
