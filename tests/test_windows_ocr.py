import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pillclerk import config, ocr


def test_windows_ocr_uses_local_script_and_filters_blank_lines(tmp_path, monkeypatch):
    image = tmp_path / "reference.png"
    image.write_bytes(b"test-only input")
    monkeypatch.setattr(ocr.sys, "platform", "win32")
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps({"lines": [" TestOnly ", ""]}))
    monkeypatch.setattr(ocr.subprocess, "run", run)
    assert ocr.transcribe_windows(image) == ["TestOnly"]
    assert calls[0][0][-3:] == [str(image.resolve()), "-LanguageTag", config._get("WINDOWS_OCR_LANGUAGE", "en-US")]
    assert calls[0][1]["timeout"] == 60
    assert "shell" not in calls[0][1]


def test_windows_backend_routes_locally_and_rejects_unsupported_host(tmp_path, monkeypatch):
    monkeypatch.setenv("EXTRACT_BACKEND", "windows")
    monkeypatch.setattr(ocr, "transcribe_windows", lambda p: ["local"])
    assert config.extract_backend() == "windows"
    assert ocr.extract_from_image(str(tmp_path / "real.png")) == ["local"]


def test_windows_failure_does_not_fabricate_text(tmp_path, monkeypatch):
    image = tmp_path / "reference.png"
    image.write_bytes(b"test-only input")
    monkeypatch.setattr(ocr.sys, "platform", "win32")
    monkeypatch.setattr(ocr.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(RuntimeError, match="could not read"):
        ocr.transcribe_windows(image)
    monkeypatch.setattr(ocr.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="needs Windows"):
        ocr.transcribe_windows(image)


def test_extracted_text_requires_signoff_before_loading(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("EXTRACT_BACKEND", "manual")
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/pages/1_Scan.py"))
    at.session_state["scan_extracted"] = True
    at.session_state["scan_text"] = "Test-only source text"
    at.run()
    assert not at.exception
    assert next(b for b in at.button if b.label == "Load lines").disabled
    at.checkbox(key="scan_text_checked").check().run()
    assert not next(b for b in at.button if b.label == "Load lines").disabled
    at.text_area(key="scan_text").set_value("Edited test-only source").run()
    assert next(b for b in at.button if b.label == "Load lines").disabled
    next(b for b in at.button if b.label == "Clear").click().run()
    assert not at.exception
    assert at.text_area(key="scan_text").value == ""
    assert not at.session_state["scan_extracted"]


@pytest.mark.parametrize("output", ["invalid JSON", "[]", '{"lines":[12]}'])
def test_windows_invalid_payload_stays_unavailable(tmp_path, monkeypatch, output):
    image = tmp_path / "input.png"
    image.write_bytes(b"test-only input")
    monkeypatch.setattr(ocr.sys, "platform", "win32")
    monkeypatch.setattr(ocr.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=output))
    with pytest.raises(RuntimeError, match="invalid result"):
        ocr.transcribe_windows(image)
