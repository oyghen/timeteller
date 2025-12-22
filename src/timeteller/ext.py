__all__ = ("Duration", "datesub", "parse")

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import duckdb
from dateutil import parser
from dateutil.relativedelta import relativedelta

import timeteller as tt


@dataclass(frozen=True, slots=True)
class Duration:
    """Non-negative length of time that elapsed between two dates or times.

    Examples
    --------
    >>> import timeteller as tt
    >>> duration = tt.ext.Duration("2024-07-01 13:00:00", "2024-08-02 14:00:01")
    >>> duration
    Duration(2024-07-01T13:00:00, 2024-08-02T14:00:01)
    >>> duration.is_zero
    False
    >>> duration.as_default()
    '1mo 1d 1h 1s'
    >>> duration.as_default() == str(duration)
    True
    >>> duration.as_compact_days()
    '32d 1h 1s'
    >>> duration.as_compact_weeks()
    '1mo 1d 1h 1s'
    >>> duration.as_iso()
    'P1M1DT1H1S'
    >>> duration.as_total_seconds()
    '2_768_401s'
    """

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
        """Return True if duration is zero, i.e. all parts are zero.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("13:00:00", "13:00:00")
        >>> duration.is_zero
        True
        """
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
        """Return seconds and microseconds as a formatted string.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("13:00:00", "13:00:00.123456")
        >>> duration.seconds, duration.microseconds, duration.formatted_seconds
        (0, 123456, '0.123456')

        >>> duration = tt.ext.Duration("13:00:00", "13:00:01")
        >>> duration.seconds, duration.microseconds, duration.formatted_seconds
        (1, 0, '1')

        >>> duration = tt.ext.Duration("13:00:00", "13:00:01.234")
        >>> duration.seconds, duration.microseconds, duration.formatted_seconds
        (1, 234000, '1.234')
        """
        if self.microseconds:
            value = f"{self.seconds}.{self.microseconds:06d}".rstrip("0")
            return value.rstrip(".")
        if self.seconds:
            return str(self.seconds)
        return "0"

    def as_default(self) -> str:
        """Return duration as a human-readable string.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-01T14:01:01")
        >>> duration.as_default()
        '1y 1h 1m 1s'

        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-09T14:01:01")
        >>> duration.as_default()
        '1y 8d 1h 1m 1s'
        """
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
        """Return a compact human-readable duration with days as the largest unit.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-01T14:01:01")
        >>> duration.as_compact_days()
        '365d 1h 1m 1s'

        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-09T14:01:01")
        >>> duration.as_compact_days()
        '373d 1h 1m 1s'
        """
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
        """Return duration as a compact human-readable string including weeks.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-01T14:01:01")
        >>> duration.as_compact_weeks()
        '1y 1h 1m 1s'

        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-09T14:01:01")
        >>> duration.as_compact_weeks()
        '1y 1w 1d 1h 1m 1s'
        """
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
        """Return duration as an ISO 8601 duration string.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-01T14:01:01")
        >>> duration.as_iso()
        'P1YT1H1M1S'

        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-09T14:01:01")
        >>> duration.as_iso()
        'P1Y8DT1H1M1S'
        """
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
        """Return the total duration in seconds as a string.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-01T14:01:01")
        >>> duration.as_total_seconds()
        '31_539_661s'
        """
        return f"{int(round(self.total_seconds)):_}s"

    def as_custom(self, formatter: Callable[["Duration"], str]) -> str:
        """Return a custom string representation of the Duration object.

        Examples
        --------
        >>> import timeteller as tt
        >>> duration = tt.ext.Duration("2024-07-01T13:00:00", "2025-07-01T14:01:01")
        >>> duration.as_custom(lambda x: f"{x.years}y {x.months}mo {x.days}d")
        '1y 0mo 0d'
        """
        return formatter(self)

    def _get_seconds_part(self, num_parts: int, unit: str = "s") -> str:
        """Return the seconds formatted with the given unit."""
        if self.formatted_seconds != "0":
            return f"{self.formatted_seconds}{unit}"
        return f"0{unit}" if num_parts == 0 else ""

    def __repr__(self) -> str:
        start = tt.stdlib.isoformat(self.start_dt)
        end = tt.stdlib.isoformat(self.end_dt)
        return f"{self.__class__.__name__}({start}, {end})"

    def __str__(self) -> str:
        return self.as_default()


def datesub(
    part: str,
    start: tt.stdlib.DateTimeLike,
    end: tt.stdlib.DateTimeLike,
) -> int:
    """Return the number of complete partitions between times.

    Function computes the difference of fully elapsed time units between the start and
    end date/time values using DuckDB's datesub time function for date subtraction.
    [1]_ [2]_

    References
    ----------
    .. [1] "Time Functions: datesub", DuckDB Documentation,
           `<https://duckdb.org/docs/stable/sql/functions/time>`_
    .. [2] "Date Part Functions", DuckDB Documentation,
            `<https://duckdb.org/docs/stable/sql/functions/datepart.html>`_

    Examples
    --------
    >>> import timeteller as tt
    >>> start_time = "2000-01-01 00:00:00.012345"
    >>> end_time = "2025-01-01 23:59:59.123456"
    >>> tt.ext.datesub("decades", start_time, end_time)
    2
    >>> tt.ext.datesub("years", start_time, end_time)
    25
    >>> tt.ext.datesub("quarter", start_time, end_time)
    100
    >>> tt.ext.datesub("months", start_time, end_time)
    300
    >>> tt.ext.datesub("days", start_time, end_time)
    9132
    >>> tt.ext.datesub("hours", start_time, end_time)
    219191
    >>> tt.ext.datesub("minutes", start_time, end_time)
    13151519
    >>> tt.ext.datesub("seconds", start_time, end_time)
    789091199

    >>> tt.ext.datesub("days", "2024-07-01", "2024-07-07")
    6
    """
    query = f"SELECT datesub('{part}', ?, ?)"
    parameters = parse(start), parse(end)
    return duckdb.execute(query, parameters).fetchone()[0]


def parse(
    value: tt.stdlib.DateTimeLike,
    formats: str | Sequence[str] | None = None,
) -> dt.datetime:
    """Return a datetime.datetime parsed from a datetime, date, time, or string."""
    try:
        return tt.stdlib.parse(value, formats)
    except ValueError:
        return parser.parse(value, default=dt.datetime(1900, 1, 1, 0, 0, 0, 0))
