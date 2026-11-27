import json
from pathlib import Path


def result():
    return json.loads(Path("src/review.json").read_text(encoding="utf-8"))


def test_review_is_valid_json_with_expected_shape():
    value = result()
    assert set(value) == {"verdict", "findings", "summary"}
    assert isinstance(value["findings"], list)


def test_material_defect_blocks_merge():
    assert result()["verdict"] == "CHANGES_REQUIRED"


def test_authentication_module_is_identified():
    findings = result()["findings"]
    assert any(item.get("path") == "src/app/auth.py" for item in findings)
