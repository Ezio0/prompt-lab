import pytest

from prompt_lab.core.version_manager import (
    VersionAlreadyExistsError,
    VersionManager,
    VersionNotFoundError,
)


def test_add_version_writes_immutable_json_and_hashes_content(tmp_path):
    manager = VersionManager(tmp_path)

    version = manager.add_version("v1", "First prompt", author="alice")

    stored = tmp_path / ".prompt-lab" / "versions" / "v1.json"
    assert stored.is_file()
    assert version.id == "v1"
    assert version.content_hash.startswith("sha256:")
    assert version.author == "alice"


def test_get_version_returns_stored_version(tmp_path):
    manager = VersionManager(tmp_path)
    manager.add_version("v1", "First prompt", change_note="initial")

    version = manager.get_version("v1")

    assert version.prompt_text == "First prompt"
    assert version.change_note == "initial"


def test_list_versions_is_reverse_chronological_and_limited(tmp_path, monkeypatch):
    manager = VersionManager(tmp_path)
    timestamps = iter(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"])
    monkeypatch.setattr(manager, "_timestamp", lambda: next(timestamps))
    manager.add_version("v1", "First")
    manager.add_version("v2", "Second")

    assert [version.id for version in manager.list_versions()] == ["v2", "v1"]
    assert [version.id for version in manager.list_versions(limit=1)] == ["v2"]


def test_diff_returns_unified_diff(tmp_path):
    manager = VersionManager(tmp_path)
    manager.add_version("v1", "line one\nline two\n")
    manager.add_version("v2", "line one\nline changed\n")

    diff = manager.diff("v1", "v2")

    assert "--- v1" in diff
    assert "+++ v2" in diff
    assert "-line two" in diff
    assert "+line changed" in diff


def test_duplicate_name_is_rejected_to_preserve_immutability(tmp_path):
    manager = VersionManager(tmp_path)
    manager.add_version("v1", "First")

    with pytest.raises(VersionAlreadyExistsError, match="E_ALREADY_EXISTS"):
        manager.add_version("v1", "Changed")

    assert manager.get_version("v1").prompt_text == "First"


def test_get_missing_version_raises_not_found_error(tmp_path):
    with pytest.raises(VersionNotFoundError, match="E_VERSION_NOT_FOUND"):
        VersionManager(tmp_path).get_version("missing")


def test_add_version_preserves_change_metadata(tmp_path):
    version = VersionManager(tmp_path).add_version(
        "v2", "Updated", changed_from="v1", changed_var="params", change_note="lower temp"
    )

    assert (version.changed_from, version.changed_var, version.change_note) == (
        "v1",
        "params",
        "lower temp",
    )
