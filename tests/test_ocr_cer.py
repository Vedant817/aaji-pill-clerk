from eval.ocr_cer import cer, e4b_available, levenshtein


def test_levenshtein_and_cer() -> None:
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("kitten", "sitting") == 3
    assert cer("abc", "abc") == 0.0
    assert cer("abc", "ab") == 1 / 3
    assert cer("", "x") == 1.0
    assert cer("", "") == 0.0


def test_e4b_not_claimed_when_missing(monkeypatch) -> None:
    from pillclerk import ocr
    def unavailable():
        raise ConnectionError("test-only unavailable daemon")
    monkeypatch.setattr(ocr, "local_ocr_client", unavailable)
    assert e4b_available() is False


def test_available_model_does_not_require_cli_on_path(monkeypatch):
    from types import SimpleNamespace
    from pillclerk import config, ocr
    monkeypatch.setattr(ocr, "local_ocr_client", lambda: SimpleNamespace(
        list=lambda: SimpleNamespace(models=[SimpleNamespace(model=config.OLLAMA_EXTRACT_MODEL)])))
    assert e4b_available()


def test_unverified_development_labels_cannot_be_cer_gold(monkeypatch, tmp_path):
    import json
    from eval import ocr_cer
    monkeypatch.setattr(ocr_cer, "OUT", tmp_path / "cer.json")
    monkeypatch.setattr("sys.argv", ["ocr_cer"])
    def pending(*args):
        raise ValueError("Independent human annotations pending")
    monkeypatch.setattr(ocr_cer, "final_gold", pending)
    monkeypatch.setattr(ocr_cer, "e4b_available", lambda: (_ for _ in ()).throw(AssertionError("Must not run OCR without human gold")))
    assert ocr_cer.main() == 0
    assert json.loads(ocr_cer.OUT.read_text())["cer"] is None
