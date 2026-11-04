import datetime as dt
import math
from typing import Annotated

import timeteller as tt
import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True)

FORMATS = [r"%Y-%m-%d", r"%Y-%m-%dT%H:%M:%S"]


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool, typer.Option("--version", is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    if version:
        typer.echo(tt.__version__)
        raise typer.Exit()


@app.command()
def duration(
    start: Annotated[
        dt.datetime,
        typer.Argument(formats=FORMATS, help="Start date/time."),
    ],
    end: Annotated[
        dt.datetime | None,
        typer.Argument(
            formats=FORMATS, help="End date/time.", show_default="today/now"
        ),
    ] = None,
) -> None:
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
    start: Annotated[
        dt.datetime,
        typer.Argument(formats=FORMATS, help="Start date/time."),
    ],
    end: Annotated[
        dt.datetime | None,
        typer.Argument(
            formats=FORMATS, help="End date/time.", show_default="today/now"
        ),
    ] = None,
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
    reference: str = typer.Argument(
        help=r"Reference date/time. Use: today, now, %Y-%m-%d, or %Y-%m-%dT%H:%M:%S."
    ),
    operation: str = typer.Argument(help="Operation to perform. Use 'add' or 'sub'."),
    value: float = typer.Argument(help="Finite number of time units to offset."),
    unit: str = typer.Argument(help="Time unit (e.g., decades, years, months, days)"),
) -> None:
    """Show date or time offset by adding or subtracting specified time units.

    Example:
    $ timeteller offset 1991-02-20 add 3 decades
    $ timeteller offset today add 3 days
    $ timeteller offset now sub 2 hours
    $ timeteller offset 2024-01-01T12:00:00 add 5.5 hours
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
    if not math.isfinite(value):
        raise typer.BadParameter("Offset value must be finite")
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
