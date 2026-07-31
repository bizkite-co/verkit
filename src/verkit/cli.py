import argparse
import sys

from rich.console import Console

from verkit.inspector import inspect_committed, inspect_project
from verkit.promoter import promote_version
from verkit.tagger import release_version, tag_version


def main():
    parser = argparse.ArgumentParser(
        prog="verkit",
        description="Polyglot project version inspector, promoter, tagger, and release workflow tool",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # verkit inspect
    subparsers.add_parser("inspect", help="Inspect working tree and HEAD version")

    # verkit promote <major|minor|patch>
    promote_p = subparsers.add_parser("promote", help="Bump version and commit/amend")
    promote_p.add_argument("part", choices=["major", "minor", "patch"])
    promote_p.add_argument(
        "--no-amend",
        dest="allow_amend",
        action="store_false",
        help="Always create a new commit",
    )

    # verkit tag
    tag_p = subparsers.add_parser("tag", help="Create git tag on HEAD and push")
    tag_p.add_argument(
        "--no-push",
        dest="push",
        action="store_false",
        help="Skip pushing to origin",
    )

    # verkit release <major|minor|patch>
    rel_p = subparsers.add_parser("release", help="Atomic promote + tag + push")
    rel_p.add_argument("part", choices=["major", "minor", "patch"])
    rel_p.add_argument(
        "--no-push",
        dest="push",
        action="store_false",
        help="Promote and tag locally only",
    )

    args = parser.parse_args()
    console = Console()

    if not args.command or args.command == "inspect":
        info = inspect_project()
        committed = inspect_committed()
        console.print(f"[bold blue]Working version:[/bold blue] {info.version} (from {info.source or 'unknown'})")
        console.print(f"[dim]Committed version (HEAD):[/dim] {committed.version}")
        return

    try:
        if args.command == "promote":
            promote_version(args.part, console=console, allow_amend=getattr(args, "allow_amend", True))
        elif args.command == "tag":
            tag_version(console=console, push=getattr(args, "push", True))
        elif args.command == "release":
            release_version(args.part, console=console, push=getattr(args, "push", True))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
