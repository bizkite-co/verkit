import os
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
    head = res.stdout.strip()

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


def _bump_project_version(part: str, project_root: Path, source: str) -> str:
    if source == "pyproject.toml":
        res = subprocess.run(
            [
                "bump-my-version",
                "bump",
                part,
                "--config-file",
                str(project_root / "pyproject.toml"),
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            shell=(os.name == "nt"),
        )
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(
                f"bump-my-version failed (is it installed in environment?): {err}"
            )
    elif source == "package.json":
        res = subprocess.run(
            ["npm", "version", part, "--no-git-tag-version"],
            capture_output=True,
            text=True,
            cwd=project_root,
            shell=(os.name == "nt"),
        )
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(f"npm version failed: {err}")
    else:
        raise RuntimeError(
            f"Cannot bump version: unsupported project file source {source!r}"
        )

    new_info = get_project_version(project_root)
    if new_info.version == "unknown":
        raise RuntimeError("Version bump ran but new version could not be read.")
    return new_info.version


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
