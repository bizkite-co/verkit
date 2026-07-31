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
