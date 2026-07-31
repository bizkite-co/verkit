import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class VersionInfo:
    version: str
    source: Optional[str] = None


def get_project_version(root: Optional[Path] = None) -> VersionInfo:
    """Read the current project version from various project files (working tree)."""
    root = root or Path.cwd()

    # Check pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            with pyproject.open("r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'version\s*=\s*"(.*?)"', content)
                if match:
                    return VersionInfo(version=match.group(1), source="pyproject.toml")
        except Exception:
            pass

    # Check package.json
    package_json = root / "package.json"
    if package_json.exists():
        try:
            with package_json.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if "version" in data:
                    return VersionInfo(version=data["version"], source="package.json")
        except Exception:
            pass

    # Check Cargo.toml (Rust)
    cargo = root / "Cargo.toml"
    if cargo.exists():
        try:
            with cargo.open("r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'^version\s*=\s*"(.*?)"', content, re.MULTILINE)
                if match:
                    return VersionInfo(version=match.group(1), source="Cargo.toml")
        except Exception:
            pass

    # Check *.csproj (.NET)
    for csproj in root.glob("*.csproj"):
        try:
            with csproj.open("r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r"<Version>(.*?)</Version>", content)
                if match:
                    return VersionInfo(version=match.group(1), source=csproj.name)
        except Exception:
            pass

    # Check pom.xml (Java/Maven)
    pom = root / "pom.xml"
    if pom.exists():
        try:
            with pom.open("r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r"<version>(.*?)</version>", content)
                if match:
                    return VersionInfo(version=match.group(1), source="pom.xml")
        except Exception:
            pass

    # Check build.gradle (Java/Gradle)
    gradle_kts = root / "build.gradle.kts"
    gradle = root / "build.gradle"
    gradle_file = None
    if gradle_kts.exists():
        gradle_file = gradle_kts
    elif gradle.exists():
        gradle_file = gradle

    if gradle_file:
        try:
            with gradle_file.open("r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'version\s*=\s*["\'](.*?)["\']', content)
                if match:
                    return VersionInfo(version=match.group(1), source=gradle_file.name)
        except Exception:
            pass

    return VersionInfo(version="unknown", source=None)


def inspect_project(root: Optional[Path] = None) -> VersionInfo:
    return get_project_version(root)


def inspect_committed(root: Optional[Path] = None) -> VersionInfo:
    """Read the version from HEAD (committed code), not working tree."""
    files_to_check = [
        ("pyproject.toml", r'version\s*=\s*"(.*?)"'),
        ("package.json", None),
        ("Cargo.toml", r'^version\s*=\s*"(.*?)"'),
    ]

    git_c = ["git"]
    if root is not None:
        git_c = ["git", "-C", str(root)]

    for filename, pattern in files_to_check:
        try:
            result = subprocess.run(
                git_c + ["show", f"HEAD:{filename}"],
                capture_output=True,
                text=True,
                check=False,
                shell=(os.name == "nt"),
            )
            if result.returncode == 0:
                if filename == "package.json":
                    try:
                        data = json.loads(result.stdout)
                        if "version" in data:
                            return VersionInfo(
                                version=data["version"], source="package.json"
                            )
                    except Exception:
                        pass
                elif pattern:
                    match = re.search(pattern, result.stdout, re.MULTILINE)
                    if match:
                        return VersionInfo(version=match.group(1), source=filename)
        except Exception:
            pass

    return VersionInfo(version="unknown", source=None)
