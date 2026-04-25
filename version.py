#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "purekit",
#   "typer",
# ]
# ///

import re
import subprocess
import tomllib
from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated

import purekit as pk  # type: ignore
import typer

LIB_NAME = "timeteller"
CLI_NAME = "timeteller-cli"

ROOT = Path(__file__).resolve().parent
ROOT_PYPROJECT = ROOT / "pyproject.toml"
LIB_PYPROJECT = ROOT / "packages" / LIB_NAME / "pyproject.toml"
CLI_PYPROJECT = ROOT / "packages" / CLI_NAME / "pyproject.toml"


class BumpType(StrEnum):
    """Supported version bump types."""

    major = auto()
    minor = auto()
    patch = auto()
    stable = auto()
    alpha = auto()
    beta = auto()
    rc = auto()
    post = auto()
    dev = auto()


def main(
    bump_types: Annotated[
        list[BumpType], typer.Option("--bump", help="Specify bump type.")
    ],
) -> None:
    """Bump versions for lockstep release.

    Example:
    $ uv run version.py --bump minor
    $ uv run version.py --bump minor --bump rc
    $ uv run version.py --bump rc
    $ uv run version.py --bump stable
    """
    bump_versions(bump_types)
    bumped_version = project_version(ROOT_PYPROJECT)
    check_versions(bumped_version)
    update_dependency_pin(bumped_version)
    refresh_lockfile()
    commit_bump(bumped_version)
    tag_commit(bumped_version)
    typer.echo(pk.text.headline(typer.style("if successful", fg=typer.colors.YELLOW)))
    typer.echo("git push && git push --tags")


def bump_versions(bumps: list[BumpType]) -> None:
    """Bump the workspace root and package versions in one uv-style sequence."""
    run(*uv_version_args(bumps))
    run(*uv_version_args(bumps, package=LIB_NAME))
    run(*uv_version_args(bumps, package=CLI_NAME))


def uv_version_args(bumps: list[BumpType], package: str | None = None) -> list[str]:
    """Build a uv version command that preserves bump order."""
    args = ["uv", "version", "--frozen"]

    for bump in bumps:
        args.extend(["--bump", bump.value])

    if package is not None:
        args.extend(["--package", package])

    return args


def project_version(path: Path) -> str:
    """Read the project version from a pyproject.toml file."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data["project"]["version"]


def check_versions(version: str) -> None:
    """Verify that package versions match the workspace version."""
    lib_version = project_version(LIB_PYPROJECT)
    cli_version = project_version(CLI_PYPROJECT)

    if lib_version != version or cli_version != version:
        raise RuntimeError(
            f"Version mismatch: root={version}, lib={lib_version}, cli={cli_version}"
        )


def update_dependency_pin(version: str) -> None:
    """Update the CLI package's exact dependency pin on the library."""
    cli_text = CLI_PYPROJECT.read_text(encoding="utf-8")
    updated = replace_exact_pin(cli_text, LIB_NAME, version)

    if updated != cli_text:
        CLI_PYPROJECT.write_text(updated, encoding="utf-8")


def replace_exact_pin(text: str, package: str, version: str) -> str:
    """Replace an exact dependency pin with a new version."""
    pattern = rf"({re.escape(package)}\[plus\]==)([^\s,;\"']+)"
    updated, count = re.subn(pattern, rf"\g<1>{version}", text, count=1)

    if count != 1:
        raise RuntimeError(f"Could not find exact pin for {package} in {CLI_PYPROJECT}")

    return updated


def refresh_lockfile() -> None:
    """Regenerate the uv lockfile."""
    run("uv", "lock")


def commit_bump(version: str) -> None:
    """Stage changed files and commit the version bump."""
    prefix = typer.style("Created commit", fg=typer.colors.GREEN, bold=True)
    message = f"chore(release): bump version to v{version}"

    # Stage only the files this script mutates
    files = (ROOT_PYPROJECT, LIB_PYPROJECT, CLI_PYPROJECT, "uv.lock")
    for file_name in files:
        run("git", "add", str(file_name))

    run("git", "commit", "-m", message)

    typer.echo(f"{prefix} {message}")


def tag_commit(version: str) -> None:
    """Create an annotated release tag for the version."""
    prefix = typer.style("Created tag", fg=typer.colors.GREEN, bold=True)
    tag = f"v{version}"

    run("git", "tag", "-a", tag, "-m", tag)

    typer.echo(f"{prefix} {tag}")


def run(*args: str) -> None:
    """Run a command in the repository root."""
    subprocess.run(args, check=True, cwd=ROOT)


if __name__ == "__main__":
    typer.run(main)
