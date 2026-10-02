from pathlib import Path

import pytest

from pillclerk.privacy import PrivacyError, assert_gemini_eval_set, is_photo_path
from pillclerk.public_data import (
    TITLE_HMR,
    gold_overlaps_train,
    near_duplicates,
    parse_medicine_name,
    set_title,
)


def test_display_name_is_public_hmr() -> None:
    assert TITLE_HMR == "Public real-world set: HMR-100 (India)"
    assert set_title("hmr100", 0) == "Public real-world set: HMR-100 (India), n=0"
    readme = Path("README.md").read_text(encoding="utf-8")
    notice = Path("NOTICE").read_text(encoding="utf-8")
    results = Path("eval/results.md").read_text(encoding="utf-8")
    assert TITLE_HMR in readme
    assert TITLE_HMR in notice
    assert TITLE_HMR in results
    assert "CC BY-ND 4.0" in notice
    assert "10.17632/k62rfd23kz" in notice
    assert "Never call it family data" in results
    assert "arXiv 2410.09729" in notice


def test_download_script_and_gitignore() -> None:
    sh = Path("scripts/download_public.sh").read_text(encoding="utf-8")
    py = Path("scripts/download_public.py").read_text(encoding="utf-8")
    assert "chaithanyakota/100-handwritten-medical-records" in sh
    assert "CC BY-ND" in sh
    assert "https://data.mendeley.com/public-api/zip/k62rfd23kz/download/2" in py
    assert "etag_timeout" in py
    assert py.index("HMR_PARQUET") < py.index("hf_hub_download")
    gi = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/public/" in gi
    assert Path("data/public_labels/hmr100_gold.jsonl").is_file()
    notice = Path("NOTICE").read_text(encoding="utf-8")
    assert "Chaithanya Kota" in notice and "Tavish Mankash" in notice
    assert "Dipto Saha" in notice


def test_refuse_daily_zero_without_ask() -> None:
    from pillclerk.public_data import refuse_daily_zero_dose

    assert refuse_daily_zero_dose(kind="daily", morning=0, afternoon=0, night=0, ask=False)
    assert not refuse_daily_zero_dose(kind="daily", morning=0, afternoon=0, night=0, ask=True)
    assert not refuse_daily_zero_dose(kind="daily", morning=1, afternoon=0, night=0, ask=False)
    assert not refuse_daily_zero_dose(kind="prn", morning=0, afternoon=0, night=0, ask=False)


def test_prefill_from_hint_and_first_30_pages() -> None:
    from pillclerk.public_data import HMR_TARGET_PAGES, prefill_from_hint, work_items

    stub = prefill_from_hint("JANUMET 50/1000MG TAB")
    assert stub["form"] == "tab"
    assert stub["strength"]
    assert "JANUMET" in stub["drug"]
    assert stub["line"] == "JANUMET 50/1000MG TAB"
    items = work_items("hmr100", max_pages=HMR_TARGET_PAGES)
    pages = {it["image"].name for it in items}
    assert len(pages) == HMR_TARGET_PAGES
    assert len(items) >= 80
    src = Path("app/pages/5_Label_REAL.py").read_text(encoding="utf-8")
    assert "Labelled" in src
    assert "Prefill" in src
    assert "Keyboard" in src
    assert "A** accept" in src or "**A** accept" in src
    hmr = Path("scripts/run_hmr_eval_if_ready.py").read_text(encoding="utf-8")
    for name in ("b0_fair", "ft2", "ft3", "gemma31_json"):
        assert name in hmr
    assert "n < 100" in hmr


def test_parse_medicine_name_and_near_dup() -> None:
    p = parse_medicine_name("MONTAIR FX TAB")
    assert p["drug"] == "MONTAIR FX"
    assert p["form"] == "tab"
    p2 = parse_medicine_name("JANUMET 50/1000MG TAB")
    assert p2["form"] == "tab"
    assert p2["strength"]
    hits = near_duplicates("this line is not in train.jsonl xyzzy-unique-token")
    assert hits == []
    assert gold_overlaps_train("hmr100") == []


def test_public_images_blocked_gold_text_allowlisted() -> None:
    assert is_photo_path(Path("data/public/hmr100/hmr_000.jpg"))
    with pytest.raises(PrivacyError):
        assert_gemini_eval_set(Path("data/public/hmr100/hmr_000.jpg"))
    allowed = assert_gemini_eval_set(Path("data/public_labels/hmr100_gold.jsonl"))
    assert allowed.name == "hmr100_gold.jsonl"
