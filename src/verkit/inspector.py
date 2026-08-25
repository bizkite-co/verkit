import importlib.metadata
import json
import os
import re
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console


def get_installed_version(package_name: str) -> str:
    """Read the installed package version via importlib.metadata."""
    try:
        return importlib.metadata.version(package_name)
    except Exception:
        return "unknown"


def get_latest_pypi_version(package_name: str, timeout: int = 4) -> Optional[str]:
    """Fetch the latest version of a package from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.load(response)
            return data["info"]["version"]
    except Exception:
        return None


def display_version_info(
    console: Console,
    package_name: str,
    root: Optional[Path] = None,
    upgrade_cmd: Optional[str] = None,
):
    """Display running, PyPI, and local project version information."""
    tool_v = get_installed_version(package_name)
    console.print(f"[bold blue]Running version:[/bold blue] {tool_v}")

    latest_v = get_latest_pypi_version(package_name)
    if latest_v:
        if latest_v != tool_v:
            console.print(f"[bold yellow]Latest PyPI version:[/bold yellow] {latest_v}")
            if upgrade_cmd:
                console.print(f"[dim]Run [bold]{upgrade_cmd}[/bold] to upgrade.[/dim]")
        else:
            console.print(f"[dim]Latest PyPI version:[/dim] {latest_v} (up to date)")

    try:
        info = get_project_version(root)
        if info.version != "unknown":
            console.print(
                f"[dim]Local project version:[/dim] {info.version} (from {info.source})"
            )
    except Exception:
        pass


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
