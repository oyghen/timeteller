import datetime as dt

import timeteller as tt
import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    pkg_name = tt.__name__
    pkg_version = typer.style(tt.__version__, fg=typer.colors.CYAN)

    if version:
        typer.echo(f"{pkg_name} {pkg_version}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        typer.echo(f"{pkg_name} {pkg_version} ready. See --help for usage.")
        raise typer.Exit()


START_ARG = typer.Argument(
    ...,
    formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
    help="Start date/time.",
)

END_ARG = typer.Argument(
    None,
    formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
    help="End date/time.",
    show_default="today/now",
)


REFERENCE_ARG = typer.Argument(
    ...,
    help=(
        "Reference date/time. Use: today, now, or (%Y-%m-%d|%Y-%m-%dT%H:%M:%S) format."
    ),
)


@app.command()
def duration(start: dt.datetime = START_ARG, end: dt.datetime | None = END_ARG) -> None:
    """Show duration summary between two dates or times.

    Example:
    $ timeteller duration 1991-02-20
    """
    start_dt = tt.plus.parse(start)
    start_iso = tt.core.isoformat(start_dt)
    is_date_fmt = len(start_iso) == len("YYYY-MM-DD")
    if end is None:
        end_dt = dt.date.today() if is_date_fmt else dt.datetime.now()
    else:
        end_dt = tt.plus.parse(end)

    d = tt.plus.Duration(start_dt, end_dt)

    gray = "#666666"
    table = Table(header_style=gray, style=gray)
    table.add_column("", justify="left", style="#FFB270", no_wrap=True)
    table.add_column("value", justify="right", style="#FFEC71", no_wrap=True)
    table.add_column("comment", justify="right", style=gray, no_wrap=True)

    table.add_row("start", tt.core.isoformat(d.start_dt), d.start_dt.strftime("%A"))
    if end is None:
        comment = "today" if is_date_fmt else "now"
    else:
        comment = d.end_dt.strftime("%A")
    table.add_row("end", tt.core.isoformat(d.end_dt), comment)
    table.add_row("duration", str(d), "elapsed time")

    num_days = tt.plus.datesub("days", d.start_dt, d.end_dt) + 1
    num_days_text = "1 day" if num_days == 1 else f"{num_days:_} days"
    table.add_row("day count", num_days_text, "start/end incl.")

    console.print(table)


@app.command()
def datesub(
    start: dt.datetime = START_ARG,
    end: dt.datetime | None = END_ARG,
    unit: str = typer.Option("days", help="Time unit (e.g., decades, years, months)"),
) -> None:
    """Show the difference between two dates or times in complete time units.

    Example:
    $ timeteller datesub --unit decades 1991-02-20
    """
    start_dt = tt.plus.parse(start)
    start_iso = tt.core.isoformat(start_dt)
    is_date_fmt = len(start_iso) == len("YYYY-MM-DD")
    if end is None:
        end_dt = dt.date.today() if is_date_fmt else dt.datetime.now()
    else:
        end_dt = tt.plus.parse(end)

    result = tt.plus.datesub(unit, start_dt, end_dt)

    gray = "#666666"
    table = Table(header_style=gray, style=gray)
    table.add_column("", justify="left", style="#FFB270", no_wrap=True)
    table.add_column("value", justify="right", style="#FFEC71", no_wrap=True)
    table.add_column("comment", justify="right", style=gray, no_wrap=True)

    table.add_row("start", tt.core.isoformat(start_dt), start_dt.strftime("%A"))
    if end is None:
        comment = "today" if is_date_fmt else "now"
    else:
        comment = end_dt.strftime("%A")
    table.add_row("end", tt.core.isoformat(end_dt), comment)
    table.add_row("datesub", f"{result:_}", unit)

    console.print(table)


@app.command()
def offset(
    reference: str = REFERENCE_ARG,
    operation: str = typer.Argument(help="Operation to perform. Use 'add' or 'sub'."),
    value: int = typer.Argument(help="Number of time units to offset (>= 0)."),
    unit: str = typer.Argument(help="Time unit (e.g., decades, years, months, days)"),
) -> None:
    """Show date or time offset by adding or subtracting specified time units.

    Example:
    $ timeteller offset 1991-02-20 add 3 decades
    $ timeteller offset today add 3 days
    $ timeteller offset now sub 2 hours
    """
    token = str(reference).strip().lower()

    if token == "today":
        ref_dt = dt.date.today()
    elif token == "now":
        ref_dt = dt.datetime.now()
    else:
        ref_dt = tt.plus.parse(reference)

    op = operation.lower()
    if op not in {"add", "sub"}:
        raise typer.BadParameter("Operation must be 'add' or 'sub'")
    offset_value = value if op == "add" else -value

    offset_dt = tt.plus.offset(ref_dt, offset_value, unit)

    gray = "#666666"
    table = Table(header_style=gray, style=gray)
    table.add_column("", justify="left", style="#FFB270", no_wrap=True)
    table.add_column("value", justify="right", style="#FFEC71", no_wrap=True)
    table.add_column("comment", justify="right", style=gray, no_wrap=True)

    table.add_row("reference", tt.core.isoformat(ref_dt), ref_dt.strftime("%A"))
    table.add_row("offset", tt.core.isoformat(offset_dt), offset_dt.strftime("%A"))

    d = tt.plus.Duration(ref_dt, offset_dt)
    num_days = tt.plus.datesub("days", d.start_dt, d.end_dt) + 1
    num_days_text = "1 day" if num_days == 1 else f"{num_days:_} days"
    table.add_row("day count", num_days_text, "ref/off incl.")

    console.print(table)
