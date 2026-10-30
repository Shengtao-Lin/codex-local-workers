import complete_project_snapshot as C
import pytest


@pytest.fixture
def roots(tmp_path):
    template, dest = tmp_path / "template", tmp_path / "unit"
    for root in (template, dest):
        root.mkdir()
    for path in (
        "src/code.py",
        "tests/test_schema.py",
        "alembic/versions/migration.py",
        "alembic.ini",
    ):
        file = template / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(path, encoding="utf-8")
    return template, dest


def test_missing_project_test_dependency_is_copied_and_manifested(roots):
    template, dest = roots
    expected = C.complete(template, dest)
    assert C.inventory(dest) == expected == C.inventory(template)
    assert "alembic/versions/migration.py" in expected


def test_existing_different_file_never_overwritten_or_partial_copy(roots):
    template, dest = roots
    (dest / "alembic.ini").write_text("user", encoding="utf-8")
    with pytest.raises(ValueError, match="differs"):
        C.complete(template, dest)
    assert (dest / "alembic.ini").read_text("utf-8") == "user"
    assert not (dest / "src").exists()


def test_exact_accepted_producer_override_is_read_only(roots):
    template, dest = roots
    target = dest / "src/code.py"
    target.parent.mkdir()
    target.write_text("accepted producer", encoding="utf-8")
    overrides = {"src/code.py": C.digest(target)}
    expected = C.complete(template, dest, accepted_overrides=overrides)
    assert expected["src/code.py"] == overrides["src/code.py"]
    assert target.read_text("utf-8") == "accepted producer"


def test_missing_transfer_cannot_be_synthesized_from_template(roots):
    with pytest.raises(ValueError, match="transfer missing"):
        C.complete(*roots, accepted_overrides={"src/code.py": "a" * 64})


def test_override_does_not_expand_scope(roots):
    with pytest.raises(ValueError, match="outside"):
        C.complete(*roots, accepted_overrides={"../other.py": "a" * 64})


def test_project_cache_and_agent_authority_never_copied(roots):
    template, dest = roots
    for folder in (".agent", ".git", ".local-agents", "__pycache__"):
        (template / folder).mkdir()
        (template / folder / "secret.py").write_text("excluded", encoding="utf-8")
    C.complete(template, dest)
    assert not (dest / ".agent").exists()
    assert len(C.inventory(dest)) == 4
