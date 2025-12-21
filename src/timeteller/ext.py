__all__ = ("Duration", "parse")

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from dateutil import parser
from dateutil.relativedelta import relativedelta

import timeteller as tt


@dataclass(frozen=True, slots=True)
class Duration:
    """Immutable duration object representing the difference between two dates/times."""

    start_dt: dt.datetime
    end_dt: dt.datetime
    delta: relativedelta = field(repr=False)

    def __init__(self, start: tt.stdlib.DateTimeLike, end: tt.stdlib.DateTimeLike):
        start_dt = parse(start)
        end_dt = parse(end)

        if end_dt < start_dt:
            start_dt, end_dt = end_dt, start_dt

        object.__setattr__(self, "start_dt", start_dt)
        object.__setattr__(self, "end_dt", end_dt)
        object.__setattr__(self, "delta", relativedelta(end_dt, start_dt))

    @property
    def years(self) -> int:
        """Return the number of whole years between start and end datetime values."""
        return self.delta.years

    @property
    def months(self) -> int:
        """Return the number of whole months (excluding years)."""
        return self.delta.months

    @property
    def days(self) -> int:
        """Return the number of days (excluding months and years)."""
        return self.delta.days

    @property
    def hours(self) -> int:
        """Return the number of hours (excluding days)."""
        return self.delta.hours

    @property
    def minutes(self) -> int:
        """Return the number of minutes (excluding hours)."""
        return self.delta.minutes

    @property
    def seconds(self) -> int:
        """Return the remaining whole seconds (excluding minutes)."""
        return self.delta.seconds

    @property
    def microseconds(self) -> int:
        """Return the number of microseconds (excluding seconds)."""
        return self.delta.microseconds

    @property
    def total_seconds(self) -> float:
        """Return the total duration in seconds."""
        return (self.end_dt - self.start_dt).total_seconds()

    @property
    def is_zero(self) -> bool:
        """Return True if duration is zero, i.e. all parts are zero."""
        parts = (
            self.years,
            self.months,
            self.days,
            self.hours,
            self.minutes,
            self.seconds,
            self.microseconds,
        )
        return all(v == 0 for v in parts)

    @property
    def formatted_seconds(self) -> str:
        """Return seconds and microseconds as a formatted string."""
        if self.microseconds:
            value = f"{self.seconds}.{self.microseconds:06d}".rstrip("0")
            return value.rstrip(".")
        if self.seconds:
            return str(self.seconds)
        return "0"

    def as_default(self) -> str:
        """Return duration as a human-readable string."""
        parts: list[str] = []

        if self.years:
            parts.append(f"{self.years}y")
        if self.months:
            parts.append(f"{self.months}mo")
        if self.days:
            parts.append(f"{self.days}d")
        if self.hours:
            parts.append(f"{self.hours}h")
        if self.minutes:
            parts.append(f"{self.minutes}m")

        seconds_part = self._get_seconds_part(len(parts))
        if seconds_part:
            parts.append(seconds_part)

        return " ".join(parts)

    def as_compact_days(self) -> str:
        """Return a compact human-readable duration using days as the largest unit."""
        total = int(round(self.total_seconds))
        minutes, _ = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts: list[str] = []

        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")

        seconds_part = self._get_seconds_part(len(parts))
        if seconds_part:
            parts.append(seconds_part)

        return " ".join(parts)

    def as_compact_weeks(self) -> str:
        """Return duration as a compact human-readable string including weeks."""
        weeks, days = divmod(self.delta.days, 7)

        parts: list[str] = []

        if self.years:
            parts.append(f"{self.years}y")
        if self.months:
            parts.append(f"{self.months}mo")
        if weeks:
            parts.append(f"{weeks}w")
        if days:
            parts.append(f"{days}d")
        if self.hours:
            parts.append(f"{self.hours}h")
        if self.minutes:
            parts.append(f"{self.minutes}m")

        seconds_part = self._get_seconds_part(len(parts))
        if seconds_part:
            parts.append(seconds_part)

        return " ".join(parts)

    def as_iso(self) -> str:
        """Return duration as an ISO 8601 duration string."""
        date_parts = []
        time_parts = []

        if self.years:
            date_parts.append(f"{self.years}Y")
        if self.months:
            date_parts.append(f"{self.months}M")
        if self.days:
            date_parts.append(f"{self.days}D")

        if self.hours:
            time_parts.append(f"{self.hours}H")
        if self.minutes:
            time_parts.append(f"{self.minutes}M")

        seconds_part = self._get_seconds_part(len(time_parts), unit="S")
        if seconds_part != "0S":
            time_parts.append(seconds_part)

        if len(date_parts) == 0 and len(time_parts) == 0:
            time_parts.append("0S")

        result = ["P", *date_parts]
        if time_parts:
            result.append("T")
            result.extend(time_parts)

        return "".join(result)

    def as_total_seconds(self) -> str:
        """Return the total duration in seconds as a string."""
        return f"{int(round(self.total_seconds)):_}s"

    def as_custom(self, formatter: Callable[["Duration"], str]) -> str:
        """Return a custom string representation of the Duration object."""
        return formatter(self)

    def _get_seconds_part(self, num_parts: int, unit: str = "s") -> str:
        """Helper function to process the seconds part."""
        if self.formatted_seconds != "0":
            return f"{self.formatted_seconds}{unit}"
        return f"0{unit}" if num_parts == 0 else ""

    def _format_dt(self, value: dt.datetime) -> str:
        """Return ISO date or datetime depending on time components."""
        if value.time() == dt.time(0, 0):
            return value.date().isoformat()
        return value.isoformat()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({self._format_dt(self.start_dt)}, {self._format_dt(self.end_dt)})"
        )

    def __str__(self) -> str:
        return self.as_default()


def parse(
    value: tt.stdlib.DateTimeLike,
    formats: str | Sequence[str] | None = None,
) -> dt.datetime:
    """Return a datetime.datetime parsed from a datetime, date, time, or string."""
    try:
        return tt.stdlib.parse(value, formats)
    except ValueError:
        return parser.parse(value, default=dt.datetime(1900, 1, 1, 0, 0, 0, 0))
