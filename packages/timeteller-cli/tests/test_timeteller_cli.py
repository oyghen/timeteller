from importlib import metadata
from types import ModuleType

import pytest
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


@pytest.mark.parametrize(
    "operation, expected",
    [
        ("add", "2024-01-01T17:30:00"),
        ("sub", "2024-01-01T06:30:00"),
    ],
)
def test_offset_accepts_fractional_hours(operation: str, expected: str):
    result = CliRunner().invoke(
        app,
        ["offset", "2024-01-01T12:00:00", operation, "5.5", "hours"],
    )

    assert result.exit_code == 0
    assert expected in result.stdout


def test_offset_preserves_integer_values():
    result = CliRunner().invoke(
        app,
        ["offset", "2024-01-01T12:00:00", "add", "2", "hours"],
    )

    assert result.exit_code == 0
    assert "2024-01-01T14:00:00" in result.stdout


@pytest.mark.parametrize(
    "value, expected_message",
    [
        ("invalid", "Invalid value for"),
        ("nan", "Offset value must be finite"),
    ],
)
def test_offset_rejects_invalid_values(value: str, expected_message: str):
    result = CliRunner().invoke(
        app,
        ["offset", "2024-01-01T12:00:00", "add", value, "hours"],
    )

    assert result.exit_code == 2
    assert expected_message in result.output
