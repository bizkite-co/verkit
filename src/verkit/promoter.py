import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console

from verkit.inspector import get_project_version, inspect_committed

_VERSION_FILES = ("pyproject.toml", "package.json", "uv.lock", "Cargo.toml")


def _git(*args: str, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", str(cwd)]
    cmd.extend(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        shell=(os.name == "nt"),
    )


def _find_git_root(path: Path) -> Optional[Path]:
    res = _git("rev-parse", "--show-toplevel", cwd=path)
    if res.returncode == 0 and res.stdout.strip():
        return Path(res.stdout.strip()).resolve()
    return None


def _can_amend_version_safely(git_root: Path) -> Tuple[bool, str]:
    """Whether folding the version bump into HEAD via amend is safe."""
    res = _git("rev-parse", "HEAD", cwd=git_root)
    if res.returncode != 0 or not res.stdout.strip():
        return False, "no HEAD commit"

    tags_res = _git(
        "tag", "--points-at", "HEAD", "--format=%(refname:short)", cwd=git_root
    )
    if tags_res.returncode == 0 and tags_res.stdout.strip():
        tags = [t for t in tags_res.stdout.strip().splitlines() if t]
        return False, f"HEAD is tagged ({', '.join(tags)})"

    branch_res = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=git_root)
    branch = branch_res.stdout.strip() if branch_res.returncode == 0 else ""
    if not branch or branch == "HEAD":
        return False, "detached HEAD"

    upstream_res = _git(
        "rev-parse", "--abbrev-ref", "@{upstream}", cwd=git_root
    )
    if upstream_res.returncode != 0 or not upstream_res.stdout.strip():
        return True, "local branch has no tracking upstream"
    upstream = upstream_res.stdout.strip()

    counts = _git(
        "rev-list", "--count", f"{upstream}..HEAD", cwd=git_root
    )
    if counts.returncode != 0:
        return False, f"could not compare HEAD to {upstream}"
    try:
        ahead = int(counts.stdout.strip())
    except ValueError:
        return False, "invalid rev-list output"

    if ahead <= 0:
        return (
            False,
            f"HEAD is already published to {upstream} (ahead count: {ahead})",
        )
    return True, f"HEAD is ahead of {upstream} by {ahead} unpushed commit(s)"


def _stage_version_files(git_root: Path, project_root: Path) -> List[str]:
    staged: List[str] = []
    for name in _VERSION_FILES:
        target = project_root / name
        if target.exists():
            res = _git("add", str(target), cwd=git_root)
            if res.returncode == 0:
                try:
                    rel = str(target.relative_to(git_root))
                except ValueError:
                    rel = name
                staged.append(rel)
    return staged


def _increment_semver(current_v: str, part: str) -> str:
    """Increment a semver string (e.g. 0.1.0 -> 0.1.1) in pure Python."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current_v.strip())
    if not match:
        raise ValueError(f"Version {current_v!r} is not a valid semver X.Y.Z string")

    major, minor, patch, extra = (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        match.group(4),
    )
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump part: {part!r}")

    return f"{major}.{minor}.{patch}{extra}"


def _bump_project_version(part: str, project_root: Path, source: str) -> str:
    info = get_project_version(project_root)
    if info.version == "unknown":
        raise RuntimeError("Cannot bump version: current project version is unknown.")

    new_v = _increment_semver(info.version, part)

    if source == "pyproject.toml":
        file_path = project_root / "pyproject.toml"
        content = file_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'(version\s*=\s*)"(.*?)"', f'\\1"{new_v}"', content, count=1
        )
        file_path.write_text(updated, encoding="utf-8")

        # Also sync uv.lock if present
        uv_lock = project_root / "uv.lock"
        if uv_lock.exists():
            try:
                lock_text = uv_lock.read_text(encoding="utf-8")
                # Update package version entry in uv.lock if matching current version
                pattern = rf'(name\s*=\s*"{re.escape(project_root.name)}"\nversion\s*=\s*)"{re.escape(info.version)}"'
                if re.search(pattern, lock_text):
                    lock_updated = re.sub(pattern, f'\\1"{new_v}"', lock_text, count=1)
                    uv_lock.write_text(lock_updated, encoding="utf-8")
            except Exception:
                pass

    elif source == "package.json":
        file_path = project_root / "package.json"
        content = file_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'("version"\s*:\s*)"(.*?)"', f'\\1"{new_v}"', content, count=1
        )
        file_path.write_text(updated, encoding="utf-8")

    elif source == "Cargo.toml":
        file_path = project_root / "Cargo.toml"
        content = file_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'^(version\s*=\s*)"(.*?)"',
            f'\\1"{new_v}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        file_path.write_text(updated, encoding="utf-8")

    elif source.endswith(".csproj"):
        file_path = project_root / source
        content = file_path.read_text(encoding="utf-8")
        updated = re.sub(
            r"(<Version>)(.*?)(</Version>)", f"\\1{new_v}\\3", content, count=1
        )
        file_path.write_text(updated, encoding="utf-8")

    elif source == "pom.xml":
        file_path = project_root / "pom.xml"
        content = file_path.read_text(encoding="utf-8")
        updated = re.sub(
            r"(<version>)(.*?)(</version>)", f"\\1{new_v}\\3", content, count=1
        )
        file_path.write_text(updated, encoding="utf-8")

    elif "gradle" in source:
        file_path = project_root / source
        content = file_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'(version\s*=\s*["\'])(.*?)(["\'])', f"\\1{new_v}\\3", content, count=1
        )
        file_path.write_text(updated, encoding="utf-8")

    else:
        raise RuntimeError(
            f"Cannot bump version: unsupported project file source {source!r}"
        )

    verify_info = get_project_version(project_root)
    if verify_info.version != new_v:
        raise RuntimeError(
            f"Version bump failed: expected {new_v}, got {verify_info.version}"
        )
    return new_v


def _commit_version_bump(
    console: Optional[Console],
    git_root: Path,
    project_root: Path,
    new_v: str,
    *,
    allow_amend: bool = True,
) -> str:
    staged = _stage_version_files(git_root, project_root)
    if not staged:
        raise RuntimeError("No version files found to stage after bump.")

    diff_staged = _git("diff", "--cached", "--name-only", cwd=git_root)
    if diff_staged.returncode == 0 and diff_staged.stdout.strip():
        staged_all = set(diff_staged.stdout.strip().splitlines())
        unrelated = staged_all - set(staged)
        if unrelated:
            raise RuntimeError(
                "Refusing to commit version bump: unrelated files are staged: "
                + ", ".join(sorted(unrelated))
            )

    amend = False
    if allow_amend:
        ok, reason = _can_amend_version_safely(git_root)
        if ok:
            amend = True
            msg_res = _git("log", "-1", "--format=%B", cwd=git_root)
            existing_msg = (
                msg_res.stdout.strip()
                if msg_res.returncode == 0
                else "chore: bump version"
            )
            commit_res = _git("commit", "--amend", "-m", existing_msg, cwd=git_root)
            if commit_res.returncode != 0:
                err = (commit_res.stderr or commit_res.stdout or "").strip()
                raise RuntimeError(f"Failed to amend version bump: {err}")
            if console:
                console.print(
                    f"[dim]Amended version {new_v} into HEAD ({reason})[/dim]"
                )

    if not amend:
        msg = f"chore(release): v{new_v}"
        commit_res = _git("commit", "-m", msg, cwd=git_root)
        if commit_res.returncode != 0:
            err = (commit_res.stderr or commit_res.stdout or "").strip()
            if "nothing to commit" in err.lower():
                if console:
                    console.print(
                        f"[dim]Version bump for {new_v} produced no changes to commit.[/dim]"
                    )
            else:
                raise RuntimeError(f"Failed to commit version bump: {err}")
        else:
            if console:
                console.print(f"[bold green]Committed version bump: {msg}[/bold green]")

    committed_info = inspect_committed(git_root)
    if committed_info.version != new_v:
        raise RuntimeError(
            f"Post-commit verification failed: HEAD has version {committed_info.version!r}, "
            f"expected {new_v!r}."
        )

    return "amend" if amend else "commit"


def promote_version(
    part: str,
    *,
    project_root: Optional[Path] = None,
    console: Optional[Console] = None,
    allow_amend: bool = True,
) -> str:
    """Bump project version and commit it. Returns the new version string."""
    project_root = (project_root or Path.cwd()).resolve()
    git_root = _find_git_root(project_root)
    if not git_root:
        raise RuntimeError("Not inside a git repository.")

    working_info = get_project_version(project_root)
    if not working_info.source or working_info.version == "unknown":
        raise RuntimeError(
            "Could not find a project version file (pyproject.toml / package.json)."
        )

    pre_committed_info = inspect_committed(git_root)
    if console:
        console.print(
            f"[blue]Bumping {part} from working {working_info.version} "
            f"(HEAD {pre_committed_info.version}) via {working_info.source}...[/blue]"
        )

    new_v = _bump_project_version(part, project_root, working_info.source)
    if console:
        console.print(f"[bold green]Promoted to version {new_v}[/bold green]")
    _commit_version_bump(
        console, git_root, project_root, new_v, allow_amend=allow_amend
    )
    return new_v
