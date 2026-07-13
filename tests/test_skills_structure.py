"""Structural gates for the plugin itself: manifests, frontmatter, templates.

These are the checks that have historically regressed by hand-editing:
version drift between the two manifests, frontmatter typos, a template
ci.yml that no longer parses, and status-vocabulary drift across files.
"""
import json
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SKILLS = sorted(p for p in (REPO / "skills").iterdir() if p.is_dir())

CANONICAL_STATUSES = ["done", "in_progress", "awaiting_approval", "pending"]


def _frontmatter(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_md}: no frontmatter opener"
    return text.split("---")[1]


def test_every_skill_has_valid_frontmatter():
    assert SKILLS, "no skills found"
    for skill_dir in SKILLS:
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists(), f"{skill_dir.name}: missing SKILL.md"
        fm = _frontmatter(skill_md)
        assert len(fm) <= 1024, f"{skill_dir.name}: frontmatter over 1024 chars"
        name = re.search(r"^name: ([a-z0-9-]+)$", fm, re.M)
        assert name, f"{skill_dir.name}: bad or missing name"
        assert name.group(1) == skill_dir.name, (
            f"{skill_dir.name}: frontmatter name '{name.group(1)}' != dir name"
        )
        assert re.search(r"^description: \S", fm, re.M), (
            f"{skill_dir.name}: missing description"
        )


def test_manifests_parse_and_versions_match():
    plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])
    assert market["plugins"][0]["version"] == plugin["version"], (
        "plugin.json and marketplace.json versions differ"
    )


def test_ci_template_is_valid_yaml_with_expected_jobs():
    ci = yaml.safe_load(
        (REPO / "skills/pipeline-architect/templates/ci.yml").read_text("utf-8")
    )
    assert set(ci["jobs"]) == {"gates", "release"}
    # Least privilege: permissions live on jobs, not the workflow.
    assert "permissions" not in ci, "workflow-level permissions reintroduced"
    assert ci["jobs"]["gates"]["permissions"] == {"contents": "read"}
    assert ci["jobs"]["release"]["permissions"] == {"contents": "write"}


def test_status_vocabulary_is_consistent():
    """The canonical statuses must agree everywhere they're spelled out."""
    render = (REPO / "skills/browser-readable-project-docs/scripts/render_docs.py").read_text("utf-8")
    for status in CANONICAL_STATUSES:
        assert f'"{status}"' in render, f"render_docs.py missing status {status}"
    handoff = (REPO / "skills/session-handoff/templates/HANDOFF.md").read_text("utf-8")
    assert "blocked" not in handoff, "HANDOFF.md uses non-canonical 'blocked'"
    for status in CANONICAL_STATUSES:
        assert status in handoff, f"HANDOFF.md missing status {status}"


def test_repo_hygiene():
    assert (REPO / "LICENSE").exists()
    assert (REPO / "CHANGELOG.md").exists()
    version = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text("utf-8"))["version"]
    assert f"## {version}" in (REPO / "CHANGELOG.md").read_text("utf-8"), (
        f"CHANGELOG.md has no entry for current version {version}"
    )
