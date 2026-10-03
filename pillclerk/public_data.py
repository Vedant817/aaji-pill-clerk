"""Public photographed test set: HMR-100 (India) and optional BD-200.

Images live in gitignored data/public/. Gold (text) lives in
data/public_labels/. Images never leave the laptop.

The MIRAGE paper (arXiv 2410.09729) describes HMR-100 as simulated records
written by doctors: the handwriting and notation are real; the patients are
not. Never call this family data.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from rapidfuzz import fuzz

from pillclerk.config import ROOT
from pillclerk.filters import normalised_text
from pillclerk.schema import CheckField, Dose, Food, Form, Kind, MedLine, Unit

PUBLIC = ROOT / "data" / "public"
LABELS = ROOT / "data" / "public_labels"
HMR_DIR = PUBLIC / "hmr100"
BD_DIR = PUBLIC / "bd200"
GOLD_HMR = LABELS / "hmr100_gold.jsonl"
GOLD_BD = LABELS / "bd200_gold.jsonl"
TRAIN = ROOT / "data" / "synth" / "train.jsonl"
PHOTOS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp")

HMR_TARGET_LINES = 100
HMR_TARGET_PAGES = 30
BD_TARGET_LINES = 40
NEAR_DUP_RATIO = 90


def refuse_daily_zero_dose(*, kind: str, morning: float, afternoon: float, night: float, ask: bool) -> bool:
    """Label REAL: kind=daily with dose 0-0-0 is refused unless ASK is ticked."""
    if kind != "daily" or ask:
        return False
    return (morning + afternoon + night) == 0.0

TITLE_HMR = "Public real-world set: HMR-100 (India)"
TITLE_BD = "Public real-world set: BD-200 (Bangladesh)"

DATASETS = {
    "hmr100": {
        "id": "hmr100",
        "dir": HMR_DIR,
        "gold": GOLD_HMR,
        "title": TITLE_HMR,
        "target": HMR_TARGET_LINES,
        "pages": HMR_TARGET_PAGES,
        "license": "CC BY-ND 4.0",
    },
    "bd200": {
        "id": "bd200",
        "dir": BD_DIR,
        "gold": GOLD_BD,
        "title": TITLE_BD,
        "target": BD_TARGET_LINES,
        "pages": None,
        "license": "CC BY 4.0",
    },
}

_FORM_TOKEN: dict[str, Form] = {
    "TAB": "tab",
    "TABLET": "tab",
    "TAB.": "tab",
    "FC-TAB": "tab",
    "CAP": "cap",
    "CAPS": "cap",
    "CAPSULE": "cap",
    "SYR": "syrup",
    "SYP": "syrup",
    "SYRUP": "syrup",
    "SUSP": "syrup",
    "LIQD": "syrup",
    "INJ": "injection",
    "INJECTION": "injection",
    "INH": "inhaler",
    "INHALER": "inhaler",
    "MDI": "inhaler",
    "NEB": "inhaler",
    "DPS": "drops",
    "DROPS": "drops",
    "EAR-DPS": "drops",
    "N-DPS": "drops",
    "CREAM": "cream",
    "SACHET": "sachet",
    "SACH": "sachet",
    "PWD": "sachet",
}

_STRENGTH = re.compile(
    r"(\d+(?:\.\d+)?\s*(?:MG|MCG|MCG|IU|ML|GM|G|K|MCG)?(?:\s*/\s*\d+(?:\.\d+)?(?:\s*(?:MG|MCG|ML))?)?)",
    re.I,
)

FREQ_DOSE: dict[str, tuple[float, float, float, Kind]] = {
    "1-0-1": (1, 0, 1, "daily"),
    "1+0+1": (1, 0, 1, "daily"),
    "1-0-0": (1, 0, 0, "daily"),
    "1+0+0": (1, 0, 0, "daily"),
    "0-0-1": (0, 0, 1, "daily"),
    "0+0+1": (0, 0, 1, "daily"),
    "1-1-1": (1, 1, 1, "daily"),
    "1+1+1": (1, 1, 1, "daily"),
    "0-1-0": (0, 1, 0, "daily"),
    "OD": (1, 0, 0, "daily"),
    "BD": (1, 0, 1, "daily"),
    "TDS": (1, 1, 1, "daily"),
    "HS": (0, 0, 1, "daily"),
    "SOS": (0, 0, 0, "prn"),
    "PRN": (0, 0, 0, "prn"),
}


def set_title(dataset: str, n: int | None = None) -> str:
    meta = DATASETS[dataset]
    if n is None:
        return str(meta["title"])
    return f"{meta['title']}, n={n}"


def list_images(dataset: str) -> list[Path]:
    folder = Path(DATASETS[dataset]["dir"])
    if not folder.is_dir():
        return []
    from pillclerk.acceptance import reserved_names
    reserved = reserved_names() if dataset == "hmr100" else set()
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTOS and p.name not in reserved)


def _split_meds(raw: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[,;]+", raw or "") if p.strip()]
    return parts


def load_labels_csv(dataset: str) -> dict[str, list[str]]:
    """filename -> medicine-name list. labels.csv lists medicine names only."""
    folder = Path(DATASETS[dataset]["dir"])
    path = folder / "labels.csv"
    out: dict[str, list[str]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        if reader.fieldnames:
            fields = [f.strip().lower() for f in reader.fieldnames if f]
            file_col = next((c for c in fields if c in {"file", "filename", "image", "img", "path"}), None)
            med_col = next(
                (c for c in fields if c in {"medicines", "medicine", "labels", "drugs", "names"}),
                None,
            )
            rows = list(reader)
            images = list_images(dataset)
            for i, row in enumerate(rows):
                raw_map = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k}
                meds = _split_meds(raw_map.get(med_col or "", ""))
                if not meds and not file_col:
                    # single unnamed column of names
                    meds = _split_meds(",".join(raw_map.values()))
                name = ""
                if file_col:
                    name = Path(raw_map.get(file_col, "")).name
                if not name and i < len(images):
                    name = images[i].name
                if name:
                    out[name] = meds
        else:
            fh.seek(0)
            images = list_images(dataset)
            for i, line in enumerate(fh):
                meds = _split_meds(line.strip())
                if i < len(images) and meds:
                    out[images[i].name] = meds
    return out


def parse_medicine_name(token: str) -> dict:
    """Pull drug / strength / form hints from a labels.csv medicine string."""
    raw = re.sub(r"\s+", " ", (token or "").strip())
    form: Form | None = None
    words = raw.split()
    if words:
        last = words[-1].upper().rstrip(".")
        if last in _FORM_TOKEN:
            form = _FORM_TOKEN[last]
            words = words[:-1]
    body = " ".join(words)
    strength = None
    m = _STRENGTH.search(body)
    if m:
        strength = m.group(1).strip()
        drug = (body[: m.start()] + " " + body[m.end() :]).strip(" -")
    else:
        drug = body
    return {"drug": drug or None, "strength": strength, "form": form, "raw": raw}


def load_gold(dataset: str) -> list[dict]:
    path = Path(DATASETS[dataset]["gold"])
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def gold_index(dataset: str) -> dict[tuple[str, int], dict]:
    return {(r["image"], int(r["line_no"])): r for r in load_gold(dataset) if "image" in r and "line_no" in r}


def labelled_count(dataset: str) -> int:
    return len(gold_index(dataset))


def prefill_from_hint(token: str) -> dict:
    """labels.csv medicine string → line stub + drug/strength/form for Label REAL."""
    parsed = parse_medicine_name(token)
    line = (parsed.get("raw") or token or "").strip()
    return {
        "line": line,
        "drug": parsed.get("drug") or "",
        "strength": parsed.get("strength") or "",
        "form": parsed.get("form") or "tab",
    }


def upsert_gold(dataset: str, row: dict) -> None:
    from pillclerk.acceptance import reserved_names
    if dataset == "hmr100" and row["image"] in reserved_names():
        raise ValueError("Reserved test pages must be labelled in the independent annotation workflow")
    path = Path(DATASETS[dataset]["gold"])
    path.parent.mkdir(parents=True, exist_ok=True)
    key = (row["image"], int(row["line_no"]))
    rows = [r for r in load_gold(dataset) if (r.get("image"), int(r.get("line_no", 0))) != key]
    rows.append(row)
    rows.sort(key=lambda r: (str(r.get("image")), int(r.get("line_no", 0))))
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def work_items(dataset: str, *, max_pages: int | None = None) -> list[dict]:
    images = list_images(dataset)
    if max_pages:
        images = images[:max_pages]
    labels = load_labels_csv(dataset)
    done = gold_index(dataset)
    items: list[dict] = []
    for img in images:
        meds = labels.get(img.name) or []
        n_lines = max(len(meds), 1)
        for i in range(1, n_lines + 1):
            med = meds[i - 1] if i - 1 < len(meds) else ""
            items.append(
                {
                    "image": img,
                    "line_no": i,
                    "medicine": med,
                    "labelled": (img.name, i) in done,
                    "gold": done.get((img.name, i)),
                }
            )
    return items


def train_lines() -> list[str]:
    if not TRAIN.is_file():
        return []
    out = []
    for line in TRAIN.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line)["line"])
    return out


def near_duplicates(line: str, *, corpus: list[str] | None = None, threshold: int = NEAR_DUP_RATIO) -> list[str]:
    key = normalised_text(line)
    if not key:
        return []
    hits: list[str] = []
    for other in corpus if corpus is not None else train_lines():
        n = normalised_text(other)
        if not n:
            continue
        if n == key or fuzz.ratio(n, key) >= threshold:
            hits.append(other)
    return hits


def gold_overlaps_train(dataset: str) -> list[dict]:
    corpus = train_lines()
    bad = []
    for row in load_gold(dataset):
        hits = near_duplicates(row.get("line") or "", corpus=corpus)
        if hits:
            bad.append({"image": row.get("image"), "line_no": row.get("line_no"), "line": row.get("line"), "train": hits[:3]})
    return bad


def freq_to_dose(freq: str) -> tuple[Dose | None, Kind] | None:
    token = (freq or "").strip().upper().replace(" ", "")
    if token not in FREQ_DOSE:
        return None
    m, a, n, kind = FREQ_DOSE[token]
    if kind == "prn":
        return None, kind
    return Dose(morning=m, afternoon=a, night=n, unit="tab"), kind


def make_gold_row(
    *,
    dataset: str,
    image_name: str,
    line_no: int,
    line: str,
    med: MedLine,
    medicine_hint: str = "",
) -> dict:
    return {
        "id": f"{dataset}:{image_name}:l{line_no:02d}",
        "image": image_name,
        "line_no": int(line_no),
        "line": line.strip(),
        "gold": json.loads(med.model_dump_json()),
        "source": dataset,
        "style": "public_handwritten",
        "synthetic": False,
        "held_out": True,
        "photographed": True,
        "public_set": DATASETS[dataset]["title"],
        "medicine_hint": medicine_hint,
    }


def default_ask_flags(illegible: bool) -> list[CheckField]:
    if illegible:
        return ["drug", "dose", "schedule"]
    return []
