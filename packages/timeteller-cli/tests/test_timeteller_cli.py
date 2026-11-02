from importlib import metadata
from types import ModuleType

import timeteller
from timeteller_cli.cli import app
from typer.testing import CliRunner


def test_project_name(project_name: str, project_pkg: ModuleType):
    assert project_pkg.__name__ == project_name


def test_project_version(project_name: str, project_pkg: ModuleType):
    assert project_pkg.__version__ == metadata.version(project_name)


def test_lib_name():
    assert timeteller.__name__ == "timeteller"


def test_version_command_prints_library_version():
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == timeteller.__version__


def test_no_command_prints_help():
    result = CliRunner().invoke(app)

    assert result.exit_code == 2
    assert "Usage:" in result.stdout
    assert "Commands" in result.stdout
