import hashlib
import json

import pytest

from pillclerk import acceptance as a
from pillclerk.schema import Dose, MedLine
from scripts import prepare_acceptance as script


@pytest.fixture
def queue(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "ROOT", tmp_path)
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image = image_dir / "page.jpg"
    image.write_bytes(b"test-only image bytes")
    folder = tmp_path / "queue"
    folder.mkdir()
    (folder / "manifest.json").write_text(json.dumps({"image_directory": "images", "pages": [
        {"image": image.name, "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}))
    return folder


def save(folder, round_name, annotator, line="Test-only source", line_no=1):
    a.save_annotation(image="page.jpg", line_no=line_no, round_name=round_name, annotator=annotator,
        line=line, gold=MedLine(drug="SyntheticDrug", dose=Dose(morning=1), duration_days=5).model_dump(), folder=folder)


def complete(folder, name, actor):
    a.mark_page_complete("page.jpg", name, actor, folder)


def test_two_people_and_complete_agreement_required(queue):
    save(queue, "A", "one")
    with pytest.raises(ValueError, match="different human"):
        save(queue, "B", "ONE")
    with pytest.raises(ValueError, match="both complete"):
        a.final_gold(queue)
    complete(queue, "A", "one")
    save(queue, "B", "two")
    complete(queue, "B", "two")
    gold = a.final_gold(queue)
    assert len(gold) == 1 and gold[0]["double_checked"] and not gold[0]["synthetic"]
    (queue / "gold.jsonl").write_text(json.dumps(gold[0]) + "\n")
    with pytest.raises(ValueError, match="frozen"):
        save(queue, "A", "one")


def test_disagreement_blocks_gold_and_edits_invalidate_attestation(queue):
    save(queue, "A", "one")
    complete(queue, "A", "one")
    save(queue, "B", "two", "Different source")
    complete(queue, "B", "two")
    with pytest.raises(ValueError, match="disagreement"):
        a.final_gold(queue)
    save(queue, "B", "two")
    with pytest.raises(ValueError, match="unchanged"):
        a.final_gold(queue)
    complete(queue, "B", "two")
    assert len(a.final_gold(queue)) == 1


def test_changed_image_and_nonconsecutive_lines_rejected(queue):
    save(queue, "A", "one", line_no=2)
    save(queue, "B", "two", line_no=2)
    complete(queue, "A", "one")
    complete(queue, "B", "two")
    with pytest.raises(ValueError, match="consecutively"):
        a.final_gold(queue)
    a.page_path("page.jpg", queue).write_bytes(b"modified")
    with pytest.raises(ValueError, match="image changed"):
        a.page_path("page.jpg", queue)


def test_no_implicit_gold_defaults():
    with pytest.raises(ValueError, match="JSON object"):
        a.validate_gold([])
    with pytest.raises(ValueError, match="all gold fields"):
        a.validate_gold({"drug": "SyntheticDrug"})
    gold = MedLine(drug="SyntheticDrug", dose=Dose(morning=1)).model_dump()
    gold["dose"].pop("night")
    with pytest.raises(ValueError, match="Every dose"):
        a.validate_gold(gold)


def test_reservation_is_reproducible_excludes_development_and_duplicate_images(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "ROOT", tmp_path)
    images = tmp_path / "images"
    images.mkdir()
    for n in range(36):
        (images / f"hmr_{n:03}.jpg").write_bytes(str(n).encode())
    (images / "hmr_030.jpg").write_bytes(b"0")  # Duplicate of a development photo.
    (images / "labels.csv").write_text("file,medicines\n" + "".join(
        f"hmr_{n:03}.jpg,{('SyntheticDrug' if n != 35 else '')}\n" for n in range(36)))
    dev = tmp_path / "dev.jsonl"
    dev.write_text(json.dumps({"image": "hmr_031.jpg"}) + "\n")
    out = tmp_path / "reserved"
    manifest = script.reserve(images, dev, out, 3, 123)
    assert {p["image"] for p in manifest["pages"]} == {f"hmr_{n:03}.jpg" for n in (32, 33, 34)}
    assert script.reserve(images, dev, out, 3, 123) == manifest
    with pytest.raises(ValueError, match="Only 3"):
        script.reserve(images, dev, tmp_path / "too_many", 4, 123)


def test_reserved_pages_cannot_be_written_to_development_gold(monkeypatch):
    from pillclerk.public_data import upsert_gold
    monkeypatch.setattr(a, "reserved_names", lambda: {"reserved.jpg"})
    with pytest.raises(ValueError, match="Reserved test"):
        upsert_gold("hmr100", {"image": "reserved.jpg", "line_no": 1})


def test_label_page_starts_blank_and_hides_other_round(queue, monkeypatch):
    from pathlib import Path
    from PIL import Image
    from streamlit.testing.v1 import AppTest

    image = a.ROOT / "images/page.jpg"
    Image.new("RGB", (20, 20), "white").save(image)
    manifest = a.load_manifest(queue)
    manifest["pages"][0]["sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    (queue / "manifest.json").write_text(json.dumps(manifest))
    save(queue, "B", "other-person", "Hidden other-round answer")
    load, page, latest = a.load_manifest, a.page_path, a.latest_annotations
    monkeypatch.setattr(a, "DEFAULT_DIR", queue)
    monkeypatch.setattr(a, "load_manifest", lambda folder=queue: load(queue))
    monkeypatch.setattr(a, "page_path", lambda image: page(image, queue))
    monkeypatch.setattr(a, "latest_annotations", lambda: latest(queue))
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/pages/6_Label_Acceptance.py")).run()
    assert not at.exception
    assert all(widget.value == "" for widget in at.text_area)
    assert at.text_input[0].value == ""
    assert "Hidden other-round answer" not in str(at)
