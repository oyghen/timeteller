__all__ = ("DateTimeLike", "STRPTIME_FORMATS", "parse", "now", "timestamp", "isoformat")

import datetime as dt
import zoneinfo
from collections.abc import Sequence
from typing import Final, TypeAlias

DateTimeLike: TypeAlias = str | dt.time | dt.date | dt.datetime

STRPTIME_FORMATS: Final[tuple[str, ...]] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d_%H:%M:%S",
    "%Y-%m-%d-%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d_%H:%M",
    "%Y-%m-%d-%H:%M",
    "%Y%m%d %H%M%S",
    "%Y%m%d_%H%M%S",
    "%Y%m%d-%H%M%S",
    "%Y%m%d %H%M",
    "%Y%m%d_%H%M",
    "%Y%m%d-%H%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%Y%m%d",
    "%Y.%m.%d",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%H%M",
    "%H:%M",
    "%H%M%S",
    "%H:%M:%S",
    "T%H%M",
    "T%H:%M",
    "T%H%M%S",
    "T%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S%Z",
    "%Y-%m-%dT%H:%M:%S%Z%z",
)


def parse(
    value: DateTimeLike,
    formats: str | Sequence[str] | None = None,
) -> dt.datetime:
    """Return a datetime.datetime parsed from a datetime, date, time, or string."""
    if isinstance(value, dt.datetime):
        return value

    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)

    if isinstance(value, dt.time):
        return dt.datetime.combine(dt.date(1900, 1, 1), value)

    if not isinstance(value, str):
        raise TypeError(f"unsupported type for value {type(value).__name__!r}")

    if isinstance(formats, str):
        try:
            return dt.datetime.strptime(value, formats)
        except ValueError as exc:
            raise ValueError(f"{value=!r} does not match format={formats!r}") from exc

    if value.endswith("Z") and len(value) > 1:
        value = value[:-1] + "+00:00"

    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        # error is expected - try next strategy
        pass

    patterns = tuple(formats) if formats is not None else STRPTIME_FORMATS

    def parse_string(val: str, ptrn: str) -> dt.datetime | None:
        try:
            return dt.datetime.strptime(val, ptrn)
        except ValueError:
            return None

    for pattern in patterns:
        result = parse_string(value, pattern)
        if result is None and pattern.endswith("%S"):
            microsecond_pattern = f"{pattern}.%f"
            result = parse_string(value, microsecond_pattern)
        if result is None:
            # error is expected - try next pattern
            continue
        return result

    raise ValueError(f"unable to parse {value=!r}")


def now(timezone: str | dt.tzinfo | None = None) -> dt.datetime:
    """Return a timezone-aware datetime for the specified or local timezone."""
    if timezone is None:
        return dt.datetime.now().astimezone()

    if isinstance(timezone, dt.tzinfo):
        return dt.datetime.now(tz=timezone)

    if not isinstance(timezone, str):
        raise TypeError(f"unsupported type {type(timezone).__name__!r}")

    try:
        return dt.datetime.now(tz=zoneinfo.ZoneInfo(timezone))
    except zoneinfo.ZoneInfoNotFoundError as exc:
        choices = zoneinfo.available_timezones()
        if choices:
            message = f"invalid choice {timezone!r}; expected a value from {choices!r}"
            raise ValueError(message) from exc
        raise LookupError("no timezone names available") from exc


def timestamp(timezone: str | None = None, /, fmt: str | None = None) -> str:
    """Return a timestamp string with timezone info for the specified or local zone."""
    current = now(timezone)
    return current.isoformat() if fmt is None else current.strftime(fmt)


def isoformat(value: dt.date | dt.datetime) -> str:
    """Return ISO date when time components are zero, otherwise ISO datetime."""
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.isoformat()

    if (value.hour, value.minute, value.second, value.microsecond) == (0, 0, 0, 0):
        return value.date().isoformat()

    return value.isoformat()
