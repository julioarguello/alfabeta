"""The repository is the plugin marketplace Claude reads the skills from: a merge to main publishes them.

These checks keep a merge from publishing a plugin that Claude would refuse or load without a skill.
"""

import json
import re
from pathlib import Path
from typing import Any, cast

REPO = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO / ".claude-plugin"


def _json(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((PLUGIN_DIR / name).read_text(encoding="utf-8")))


def _frontmatter(skill_md: Path) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", skill_md.read_text(encoding="utf-8"), re.DOTALL)
    assert match, f"{skill_md.relative_to(REPO)}: no frontmatter"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_marketplace_lists_the_repository_as_the_plugin():
    marketplace = _json("marketplace.json")
    plugin = _json("plugin.json")
    entries = cast(list[dict[str, Any]], marketplace["plugins"])
    assert [entry["name"] for entry in entries] == [plugin["name"]]
    assert entries[0]["source"] == "./"


def test_plugin_has_no_version_so_every_merge_is_an_update():
    # With a version, Claude keeps the cached copy until someone bumps it; without one, it follows the commits.
    assert "version" not in _json("plugin.json")
    assert all("version" not in entry for entry in cast(list[dict[str, Any]], _json("marketplace.json")["plugins"]))


def test_every_skill_is_loadable():
    skills = sorted((REPO / "skills").glob("*/SKILL.md"))
    assert skills, "no skill under skills/"
    for skill_md in skills:
        fields = _frontmatter(skill_md)
        assert fields.get("name") == skill_md.parent.name, f"{skill_md.relative_to(REPO)}: name differs from its folder"
        assert 0 < len(fields.get("description", "")) <= 1024, (
            f"{skill_md.relative_to(REPO)}: description empty or too long"
        )


def test_no_top_level_bin_directory():
    # claude.ai and Cowork refuse a plugin with a top-level bin/.
    assert not (REPO / "bin").exists()
