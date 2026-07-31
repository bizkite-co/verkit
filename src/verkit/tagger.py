import os
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from verkit.inspector import get_project_version, inspect_committed


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


def _git_head_sha(git_root: Path) -> Optional[str]:
    res = _git("rev-parse", "HEAD", cwd=git_root)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return None


def _git_tag_target(git_root: Path, tag_name: str) -> Optional[str]:
    res = _git("rev-parse", f"refs/tags/{tag_name}^{{}}", cwd=git_root)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    res2 = _git("rev-parse", f"refs/tags/{tag_name}", cwd=git_root)
    if res2.returncode == 0 and res2.stdout.strip():
        return res2.stdout.strip()
    return None


def _push_branch_and_tag(
    console: Optional[Console],
    git_root: Path,
    tag_name: str,
    *,
    push_branch: bool = True,
):
    if push_branch:
        branch_res = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=git_root)
        branch = branch_res.stdout.strip() if branch_res.returncode == 0 else ""
        if not branch or branch == "HEAD":
            raise RuntimeError("Cannot push branch from detached HEAD state.")
        if console:
            console.print(f"[blue]Pushing branch {branch} to origin...[/blue]")
        res = _git("push", "origin", branch, cwd=git_root)
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(f"Failed to push branch {branch}: {err}")
        if console:
            console.print(f"[bold green]Pushed branch {branch}[/bold green]")

    if console:
        console.print(f"[blue]Pushing tag {tag_name} to origin...[/blue]")
    res = _git("push", "origin", tag_name, cwd=git_root)
    if res.returncode != 0:
        err = (res.stderr or res.stdout or "").strip()
        raise RuntimeError(f"Failed to push tag {tag_name}: {err}")
    if console:
        console.print(f"[bold green]Pushed tag {tag_name}[/bold green]")


def tag_version(
    *,
    project_root: Optional[Path] = None,
    console: Optional[Console] = None,
    push: bool = True,
    push_branch: bool = True,
) -> str:
    """Create ``vX.Y.Z`` on HEAD from the *committed* version and optionally push."""
    project_root = (project_root or Path.cwd()).resolve()
    git_root = _find_git_root(project_root)
    if not git_root:
        raise RuntimeError("Not inside a git repository.")

    committed_info = inspect_committed(git_root)
    if committed_info.version == "unknown":
        raise RuntimeError("Could not read version from HEAD. Promote first.")

    working_info = get_project_version(project_root)
    if working_info.version != "unknown" and working_info.version != committed_info.version:
        raise RuntimeError(
            f"Working tree version {working_info.version} differs from HEAD {committed_info.version}. "
            "Commit or discard local version edits before tagging."
        )

    tag_name = f"v{committed_info.version}"
    head = _git_head_sha(git_root)
    if not head:
        raise RuntimeError("Could not resolve HEAD.")

    existing = _git_tag_target(git_root, tag_name)
    if existing:
        head_full = _git("rev-parse", head, cwd=git_root).stdout.strip() or head
        existing_full = (
            _git("rev-parse", existing, cwd=git_root).stdout.strip() or existing
        )
        if existing_full == head_full:
            if console:
                console.print(f"[dim]Tag {tag_name} already points at HEAD[/dim]")
        else:
            raise RuntimeError(
                f"Tag {tag_name} already exists but points at {existing_full[:12]}, "
                f"not HEAD ({head_full[:12]})."
            )
    else:
        res = _git("tag", tag_name, cwd=git_root)
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(f"Failed to create tag {tag_name}: {err}")
        if console:
            console.print(
                f"[bold green]Tagged HEAD as {tag_name}[/bold green] "
                f"[dim]({head[:12]})[/dim]"
            )

    if push:
        _push_branch_and_tag(console, git_root, tag_name, push_branch=push_branch)
    elif console:
        console.print(
            f"[dim]Skipped push. When ready: git push && git push origin {tag_name}[/dim]"
        )

    return tag_name


def release_version(
    part: str,
    *,
    project_root: Optional[Path] = None,
    console: Optional[Console] = None,
    push: bool = True,
    push_branch: bool = True,
) -> Tuple[str, str]:
    """Atomic promote + tag + push release workflow."""
    from verkit.promoter import promote_version

    new_v = promote_version(part, project_root=project_root, console=console)
    tag_name = tag_version(
        project_root=project_root,
        console=console,
        push=push,
        push_branch=push_branch,
    )
    return new_v, tag_name
