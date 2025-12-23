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
    if show:
        typer.echo(f"{tt.__name__} {tt.__version__}")
        raise typer.Exit()


@app.command()
def duration(start: dt.datetime = START_ARG, end: dt.datetime | None = END_ARG) -> None:
    """Show duration summary between two dates or times."""
    start_dt = tt.ext.parse(start)
    start_iso = tt.stdlib.isoformat(start_dt)
    is_date_fmt = len(start_iso) == len("YYYY-MM-DD")
    if end is None:
        end_dt = dt.date.today() if is_date_fmt else dt.datetime.now()
    else:
        end_dt = tt.ext.parse(end)

    d = tt.ext.Duration(start_dt, end_dt)

    gray = "#666666"
    table = Table(header_style=gray, style=gray)
    table.add_column("", justify="left", style="#FFB270", no_wrap=True)
    table.add_column("value", justify="right", style="#FFEC71", no_wrap=True)
    table.add_column("comment", justify="right", style=gray, no_wrap=True)

    table.add_row("start", tt.stdlib.isoformat(d.start_dt), d.start_dt.strftime("%A"))
    if end is None:
        comment = "today" if is_date_fmt else "now"
    else:
        comment = d.end_dt.strftime("%A")
    table.add_row("end", tt.stdlib.isoformat(d.end_dt), comment)
    table.add_row("duration", str(d), "elapsed time")

    num_days = tt.ext.datesub("days", d.start_dt, d.end_dt) + 1
    num_days_text = "1 day" if num_days == 1 else f"{num_days:_} days"
    table.add_row("day count", num_days_text, "start/end incl.")

    console.print(table)


def main() -> None:
    """Canonical entry point for CLI execution."""
    app()
