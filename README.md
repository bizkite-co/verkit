# verkit

Polyglot project version inspector, promoter, tagger, and release workflow engine.

`verkit` provides a unified Python API and CLI tool to manage version releases across multi-language projects (`pyproject.toml`, `package.json`, `Cargo.toml`, `*.csproj`, `pom.xml`, `build.gradle`).

---

## Supported Ecosystems
| Project Type | Version File | Parser / Bump Engine |
| :--- | :--- | :--- |
| **Python** | `pyproject.toml` | Regex & `bump-my-version` |
| **Node.js** | `package.json` | JSON parser & `npm version` |
| **Rust** | `Cargo.toml` | Regex (`^version = "..."`) |
| **.NET** | `*.csproj` | XML Regex (`<Version>...</Version>`) |
| **Java (Maven)** | `pom.xml` | XML Regex (`<version>...</version>`) |
| **Java (Gradle)** | `build.gradle` / `.kts` | Regex (`version = "..."`) |

---

## Installation
```bash
pip install verkit
# or using uv
uv add verkit
```

---

## CLI Usage

### Inspect version info
Inspect current working tree and HEAD committed versions:
```bash
verkit inspect
```

### Promote version
Bump version (`major`, `minor`, or `patch`) and automatically commit or amend local release commit:
```bash
verkit promote minor
```

### Tag and push release
Verify HEAD is in sync, create `vX.Y.Z` git tag, and push branch + tag:
```bash
verkit tag
```

### One-shot atomic release
Combine promote, tag, and push in a single step:
```bash
verkit release patch
```

---

## Python API Usage

```python
import verkit

# 1. Inspect version info
info = verkit.inspect_project()
print(f"Working version: {info.version} (from {info.source})")

committed = verkit.inspect_committed()
print(f"HEAD committed version: {committed.version}")

# 2. Promote version
new_version = verkit.promote_version("minor")

# 3. Tag and push release
tag_name = verkit.tag_version(push=True)

# 4. Atomic release
verkit.release_version("patch", push=True)
```

---

## Shared Terminal Theme

`verkit` publishes the canonical Rich theme used across this developer's
CLIs (`task-agent`, `multi-agent-registry`, ...). It is **opt-in** — verkit
never applies the theme for you; consumers import it and apply it to their
own `Table`/`Panel` objects:

```python
from rich.console import Console
from rich.table import Table
from verkit.theme import DEFAULT as theme

console = Console()
table = Table(
    title="Portfolio",
    box=theme.table_box,          # borderless
    header_style=theme.header_style,  # "on grey23"
    padding=theme.table_padding,  # (0, 2, 0, 0)
)
console.print(table)
```

The theme is a frozen dataclass (`verkit.theme.Theme`); `DEFAULT` is the
canonical instance. Non-Python consumers (e.g. PowerShell scripts) read the
machine-readable mirror, which stays in sync via `tests/test_theme.py`:

```powershell
$theme = Invoke-RestMethod `
  https://raw.githubusercontent.com/bizkite-co/verkit/main/src/verkit/theme.json
# $theme.theme.header_style               -> "on grey23"
# $theme.theme.header_background_ansi     -> ANSI 256 index 237 background escape
# $theme.theme.header_background_rgb_hex  -> "#3a3a3a"
```
