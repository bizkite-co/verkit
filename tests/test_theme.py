import json
from pathlib import Path

from rich import box as rich_box

from verkit.theme import DEFAULT, Theme

THEME_JSON = Path(__file__).resolve().parent.parent / "src" / "verkit" / "theme.json"


def test_default_is_theme():
    assert isinstance(DEFAULT, Theme)


def test_default_values():
    assert DEFAULT.table_box is None
    assert DEFAULT.panel_box is rich_box.MINIMAL
    assert DEFAULT.table_padding == (0, 2, 0, 0)
    assert DEFAULT.header_style == "on grey23"


def test_theme_json_matches_default():
    data = json.loads(THEME_JSON.read_text(encoding="utf-8"))
    theme = data["theme"]
    assert theme["table_box"] is None
    assert theme["panel_box"] == "MINIMAL"
    assert tuple(theme["table_padding"]) == DEFAULT.table_padding
    assert theme["header_style"] == DEFAULT.header_style
    assert theme["header_background_ansi"] == "\x1b[48;5;237m"


def test_theme_is_frozen():
    try:
        DEFAULT.table_padding = (1, 1, 1, 1)
    except AttributeError:
        pass
    else:
        raise AssertionError("Theme should be immutable")