from types import SimpleNamespace

import pytest

from pillclerk import config, ocr
from pillclerk.privacy import PrivacyError


@pytest.mark.parametrize("host", ["https://ollama.com", "http://192.168.1.20:11434", "http://user:secret@localhost:11434"])
def test_image_client_rejects_remote_hosts_before_request(monkeypatch, host):
    monkeypatch.setenv("OLLAMA_HOST", host)
    with pytest.raises(PrivacyError, match="loopback"):
        ocr.local_ocr_client()


def test_cloud_tag_cannot_send_photos(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
    monkeypatch.setattr(config, "OLLAMA_EXTRACT_MODEL", "gemma4:cloud")
    with pytest.raises(PrivacyError, match="cloud"):
        ocr.local_ocr_client()


def test_remote_model_alias_rejected_before_photo_chat(monkeypatch):
    class Client:
        def _request_raw(self, *args, **kwargs):
            return SimpleNamespace(json=lambda: {"remote_host": "https://ollama.com"})
        def chat(self, **kwargs):
            pytest.fail("Photo must not be sent to a remote model alias")
    monkeypatch.setattr(ocr, "local_ocr_client", Client)
    with pytest.raises(PrivacyError):
        ocr.transcribe_local("test-only.jpg")


def test_local_connection_failure_is_visible_and_truncated_output_rejected(monkeypatch):
    import httpx
    class Client:
        def _request_raw(self, *args, **kwargs):
            return SimpleNamespace(json=lambda: {})
        def chat(self, **kwargs):
            assert kwargs["think"] is False
            raise httpx.ReadTimeout("test-only timeout")
    monkeypatch.setattr(ocr, "local_ocr_client", Client)
    with pytest.raises(RuntimeError, match="timed out"):
        ocr.transcribe_local("test-only.jpg")
    monkeypatch.setattr(Client, "chat", lambda *args, **kwargs: SimpleNamespace(done_reason="length"))
    with pytest.raises(RuntimeError, match="truncated"):
        ocr.transcribe_local("test-only.jpg")
