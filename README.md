# verkit

Polyglot project version inspector, promoter, tagger, and release workflow engine.

## Supported Project Types
- **Python**: `pyproject.toml`
- **Node.js**: `package.json`
- **Rust**: `Cargo.toml`
- **.NET**: `*.csproj`
- **Java (Maven)**: `pom.xml`
- **Java (Gradle)**: `build.gradle` / `build.gradle.kts`

## Installation
```bash
pip install verkit
```

## Python API Usage
```python
import verkit

# Inspect working tree and HEAD version
info = verkit.inspect()
print(info.working_version, info.source)

# Promote (bump) version
new_v = verkit.promote("minor")

# Tag HEAD and push
tag_name = verkit.tag()

# Promote + Tag + Push in one step
verkit.release("patch")
```

## CLI Usage
```bash
verkit inspect
verkit promote minor
verkit tag
verkit release patch
```
