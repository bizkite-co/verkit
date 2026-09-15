"""Shared visual theme for Rich terminal output across client CLIs.

This module is a *convention carrier*, not a mandate. The theme is published
here so a client project can opt in with a one-line import instead of
maintaining its own copy; importing it is never forced on consumers.

Adoption hint (Python)::

    from verkit.theme import DEFAULT as theme

    table = Table(
        title="...",
        box=theme.table_box,
        header_style=theme.header_style,
        padding=theme.table_padding,
    )
    console.print(Panel(..., box=theme.panel_box))

Because ``Theme`` is a frozen dataclass, ``DEFAULT`` can be shared or
subclassed without risk of accidental mutation.

Non-Python consumers (e.g. PowerShell scripts) should read the machine
readable mirror at ``src/verkit/theme.json`` instead of re-deriving styles:

    $theme = Invoke-RestMethod `
      https://raw.githubusercontent.com/bizkite-co/verkit/main/src/verkit/theme.json

The JSON and this dataclass are kept in sync by ``tests/test_theme.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich import box as rich_box


@dataclass(frozen=True)
class Theme:
    """Visual theme for Rich terminal output (tables, panels).

    Defaults render tables and panels in the compact report style shared
    across this developer's CLIs: borderless tables, a minimal panel border,
    and a subtle grey header band (ANSI 256 index 237).
    """

    table_box: rich_box.Box | None = None
    panel_box: rich_box.Box = rich_box.MINIMAL
    table_padding: tuple[int, int, int, int] = (0, 2, 0, 0)
    header_style: str = "on grey23"


#: The canonical theme. Client CLIs opt in with ``from verkit.theme import
#: DEFAULT``.
DEFAULT = Theme()