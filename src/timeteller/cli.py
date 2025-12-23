import datetime as dt

import typer
from rich.console import Console
from rich.table import Table

import timeteller as tt

console = Console()
app = typer.Typer(add_completion=False)


START_ARG = typer.Argument(
    ...,
    formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
    help="Specify start date or time.",
)

END_ARG = typer.Argument(
    None,
    formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
    help="Specify end date or time.",
    show_default="today/now",
)


@app.callback(invoke_without_command=True)
def version(
    show: bool = typer.Option(
        False, "--version", "-v", help="Show app version and exit."
    ),
) -> None:
    """Show the application version or a usage hint when no command is provided."""
    if show:
        typer.echo(f"{tt.__name__} {tt.__version__}")
        raise typer.Exit()
    typer.echo("No command provided. Run with --help to see available commands.")


@app.command()
def duration(start: dt.datetime = START_ARG, end: dt.datetime | None = END_ARG) -> None:
    """Print duration summary between two dates or times."""
    start_dt = tt.ext.parse(start)
    if end is None:
        start_str = tt.stdlib.isoformat(start_dt)
        is_date = len(start_str) == len("YYYY-MM-DD")
        end_dt = dt.date.today() if is_date else dt.datetime.now()
    else:
        end_dt = tt.ext.parse(end)

    dur = tt.ext.Duration(start_dt, end_dt)

    gray = "#666666"
    table = Table(header_style=gray, style=gray)
    table.add_column("", justify="left", style="#FFB270", no_wrap=True)
    table.add_column("value", justify="right", style="#FFEC71", no_wrap=True)
    table.add_column("comment", justify="right", style=gray, no_wrap=True)

    for label, date in [("start", dur.start_dt), ("end", dur.end_dt)]:
        table.add_row(label, tt.stdlib.isoformat(date), date.strftime("%A"))
    table.add_row("duration", str(dur), "elapsed time")

    num_days = tt.ext.datesub("days", dur.start_dt, dur.end_dt) + 1
    num_days_text = "1 day" if num_days == 1 else f"{num_days:_} days"
    table.add_row("day count", num_days_text, "start/end incl.")

    console.print(table)


def main() -> None:
    """Canonical entry point for CLI execution."""
    app()
