import pytest
from pathlib import Path
from verkit.inspector import inspect_project, inspect_committed

def test_inspect_python_project(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "myproject"\nversion = "1.2.3"\n')
    info = inspect_project(tmp_path)
    assert info.version == "1.2.3"
    assert info.source == "pyproject.toml"

def test_inspect_node_project(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text('{"name": "my-node-app", "version": "2.0.0"}')
    info = inspect_project(tmp_path)
    assert info.version == "2.0.0"
    assert info.source == "package.json"

def test_inspect_unknown_project(tmp_path):
    info = inspect_project(tmp_path)
    assert info.version == "unknown"
    assert info.source is None
