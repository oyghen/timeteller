import datetime as dt

import typer
from rich import print as rprint

import timeteller as tt

app = typer.Typer(add_completion=False)


@app.command()
def duration(
    start: str = typer.Argument(..., help="date"),
    end: str | None = typer.Argument(None, help="date", show_default="today"),
):
    end = dt.date.today() if end is None else end
    duration = tt.ext.Duration(start, end)
    rprint(duration.as_default())


def main() -> None:
    """Canonical entry point for CLI execution."""
    app()
