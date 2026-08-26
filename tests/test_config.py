import json

from src.core.config import DEFAULTS, Config


def test_defaults_when_file_absent(tmp_path):
    config = Config(tmp_path / "settings.json")
    assert config.get("schemaVersion") == DEFAULTS["schemaVersion"]
    assert config.get("logLevel") == "INFO"
    assert config.get("language") == "pt-BR"


def test_set_save_load_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    Config(path).set("logLevel", "DEBUG")
    assert Config(path).get("logLevel") == "DEBUG"


def test_corrupt_file_recovers_with_backup(tmp_path):
    path = tmp_path / "settings.json"
    path.write_bytes(b"\x00garbage{{{")
    config = Config(path)
    assert config.get("logLevel") == "INFO"
    assert (tmp_path / "settings.json.bak").is_file()
    assert not path.is_file()


def test_non_object_root_recovers_with_backup(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    config = Config(path)
    assert config.get("logLevel") == "INFO"
    assert (tmp_path / "settings.json.bak").is_file()


def test_deep_merge_keeps_file_values_and_adds_new_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"logLevel": "DEBUG", "custom": {"x": 1}}), encoding="utf-8")
    config = Config(path)
    assert config.get("logLevel") == "DEBUG"
    assert config.get("language") == "pt-BR"
    assert config.get("custom") == {"x": 1}
    assert config.get("overlay")["profiles"] == {}
    assert config.get("overlay")["opacity"] == 0.9
    assert config.get("start_with_windows") is False
    assert config.get("hotkey_toggle_overlay") == "F8"
    config.save()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["custom"] == {"x": 1}
    assert saved["language"] == "pt-BR"


def test_atomic_write_leaves_no_tmp_residue(tmp_path):
    path = tmp_path / "settings.json"
    config = Config(path)
    config.save()
    assert json.loads(path.read_text(encoding="utf-8"))
    assert not list(tmp_path.glob("*.tmp"))
