__all__ = ("parse",)

import datetime as dt
from collections.abc import Sequence

from dateutil import parser

import timeteller as tt


def parse(
    value: tt.core.DateTimeLike,
    formats: str | Sequence[str] | None = None,
) -> dt.datetime:
    """Return a datetime.datetime parsed from a datetime, date, time, or string."""
    try:
        return tt.core.parse(value, formats)
    except ValueError:
        return parser.parse(value, default=dt.datetime(1900, 1, 1, 0, 0, 0, 0))
