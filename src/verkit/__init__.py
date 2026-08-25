"""Polyglot project version inspector, promoter, tagger, and release engine."""

from verkit.inspector import (
    VersionInfo,
    display_version_info,
    get_installed_version,
    get_latest_pypi_version,
    inspect_committed,
    inspect_project,
)
from verkit.promoter import promote_version
from verkit.tagger import release_version, tag_version

__version__ = "0.1.1"
__all__ = [
    "VersionInfo",
    "inspect_project",
    "inspect_committed",
    "get_installed_version",
    "get_latest_pypi_version",
    "display_version_info",
    "promote_version",
    "tag_version",
    "release_version",
]
