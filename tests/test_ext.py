import datetime as dt
from collections.abc import Callable
from dataclasses import FrozenInstanceError

import duckdb
import pytest

import timeteller as tt


class TestDuration:
    @pytest.mark.parametrize(
        "start, end, expected",
        [
            (
                "2024-07-01T13:00:00",
                "2024-07-02T13:00:01",
                "Duration(2024-07-01T13:00:00, 2024-07-02T13:00:01)",
            ),
            (
                "2024-07-01T00:00:00",
                "2024-07-02T14:00:00",
                "Duration(2024-07-01, 2024-07-02T14:00:00)",
            ),
            (
                "2024-07-01T15:00:00",
                "2024-07-02T00:00:00",
                "Duration(2024-07-01T15:00:00, 2024-07-02)",
            ),
            (
                "2024-07-01T00:00:00",
                "2024-07-02T00:00:00",
                "Duration(2024-07-01, 2024-07-02)",
            ),
        ],
    )
    def test_repr(self, start: str, end: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert repr(result) == expected

    def test_immutability(self):
        inst = tt.ext.Duration("2024-07-01T13:00:00", "2024-07-01T13:00:01")

        # trying to modify an attribute should raise an error
        for attr in ("start_dt", "end_dt", "delta"):
            with pytest.raises(FrozenInstanceError):
                setattr(inst, attr, 10)

        # trying to modify a derived attribute should raise an error
        for attr in (
            "years",
            "months",
            "days",
            "hours",
            "minutes",
            "seconds",
            "total_seconds",
        ):
            with pytest.raises(TypeError):
                setattr(inst, attr, 10)

        # adding a new attribute should fail
        with pytest.raises(TypeError):
            inst.new_attr = 10

        # dataclass with slots should not expose __dict__
        assert not hasattr(inst, "__dict__")

    def test_constructor_orders_datetimes_and_total_seconds_positive(self):
        start = dt.datetime(2025, 1, 2, 0, 0, 0)
        end = dt.datetime(2025, 1, 1, 0, 0, 0)
        result = tt.ext.Duration(start, end)

        assert repr(result) == "Duration(2025-01-01, 2025-01-02)"
        assert result.start_dt == min(start, end)
        assert result.end_dt == max(start, end)
        assert result.total_seconds > 0

    @pytest.mark.parametrize(
        "seconds, microseconds, expected",
        [
            (0, 0, "0"),
            (0, 123456, "0.123456"),
            (1, 0, "1"),
            (1, 234000, "1.234"),
        ],
    )
    def test_formatted_seconds(self, seconds: int, microseconds: int, expected: str):
        start = dt.datetime(2025, 1, 1, 13, 0, 0)
        end = start + dt.timedelta(seconds=seconds, microseconds=microseconds)
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.formatted_seconds == expected

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            ("2024-07-01T13:00:00+00:00", "2024-07-01T13:00:00+00:00", "0"),
            ("T13:00:00", "T13:00:00", "0"),
            ("T13:00:00", "T13:00:00.000123", "0.000123"),
            ("T13:00:00", "T13:00:00.123456", "0.123456"),
            ("T13:00:00", "T13:00:00.1234567", "0.123456"),
            ("T13:00:00.999999", "T13:00:00.111111", "0.888888"),
            ("T13:00:00.101010", "T13:00:00.101010", "0"),
            ("T13:00:00.101010", "T13:00:00.010101", "0.090909"),
            ("T13:00:00.1010", "T13:00:00.0101", "0.0909"),
            ("T13:00:00", "T13:00:01", "1"),
            ("T13:00:00", "T13:00:59", "59"),
            ("T13:00:00", "T13:00:59.999999", "59.999999"),
            ("T13:00:00", "T13:00:59.999000", "59.999"),
            ("T13:00:00", "T13:00:59.0", "59"),
            ("T13:00:00", "T13:01:00.0", "0"),
        ],
    )
    def test_formatted_seconds_extended(self, start: str, end: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.formatted_seconds == expected

    def test_is_zero(self):
        t = dt.datetime(2025, 6, 1, 12, 0, 0)
        result = tt.ext.Duration(t, t)
        assert result.is_zero is True
        assert result.as_iso() == "PT0S"
        assert result.as_default() == "0s"

    @pytest.mark.parametrize(
        "start, end, iso, expected",
        [
            ("13:00:00", "13:00:00", "PT0S", "0s"),
            ("13:00:00", "T13:00:00", "PT0S", "0s"),
            ("T13:00:00", "13:00:00", "PT0S", "0s"),
            ("T13:00:00", "T13:00:00", "PT0S", "0s"),
            ("2024-07-01", "2024-07-01", "PT0S", "0s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00", "PT0S", "0s"),
            ("2024-07-01T13:00:00Z", "2024-07-01T13:00:00Z", "PT0S", "0s"),
            ("2024-07-01T13:00:00+00:00", "2024-07-01T13:00:00+00:00", "PT0S", "0s"),
            ("2024-07-01T13:00:00Z+01:00", "2024-07-01T13:00:00Z+01:00", "PT0S", "0s"),
            ("2024-07-01T13:00:00+01:00", "2024-07-01T13:00:00+01:00", "PT0S", "0s"),
            ("2024-07-01T13:00:00.1", "2024-07-01T13:00:00.1", "PT0S", "0s"),
            ("2024-07-01T13:00:00+01:00", "2024-07-01T14:00:00+02:00", "PT0S", "0s"),
            ("2024-07-01T14:00:00+02:00", "2024-07-01T13:00:00+01:00", "PT0S", "0s"),
        ],
    )
    def test_is_zero_extended(self, start: str, end: str, iso: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.is_zero is True
        assert result.as_iso() == iso
        assert result.as_default() == expected

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            # 1 year + 1 hour + 1 minute + 1 second
            (
                dt.datetime(2024, 7, 1, 13, 0, 0),
                dt.datetime(2025, 7, 1, 14, 1, 1),
                "1y 1h 1m 1s",
            ),
            # 1 year + 8 days + 1 hour + 1 minute + 1 second
            (
                dt.datetime(2024, 7, 1, 13, 0, 0),
                dt.datetime(2025, 7, 9, 14, 1, 1),
                "1y 8d 1h 1m 1s",
            ),
        ],
    )
    def test_as_default(self, start: dt.datetime, end: dt.datetime, expected: str):
        result = tt.ext.Duration(start, end)
        assert result.as_default() == expected

    @pytest.mark.parametrize(
        "start, end, iso, expected",
        [
            # 1x date change
            ("2024-07-01", "2025-07-01", "P1Y", "1y"),
            ("2024-07-01", "2024-08-01", "P1M", "1mo"),
            ("2024-07-01", "2024-07-02", "P1D", "1d"),
            ("2024-07-01T13:00:00", "2025-07-01T13:00:00", "P1Y", "1y"),
            ("2024-07-01T13:00:00", "2024-08-01T13:00:00", "P1M", "1mo"),
            ("2024-07-01T13:00:00", "2024-07-02T13:00:00", "P1D", "1d"),
            # 2x date changes
            ("2024-07-01", "2025-08-01", "P1Y1M", "1y 1mo"),
            ("2024-07-01", "2025-07-02", "P1Y1D", "1y 1d"),
            ("2024-07-01", "2024-08-02", "P1M1D", "1mo 1d"),
            ("2024-07-01T13:00:00", "2025-08-01T13:00:00", "P1Y1M", "1y 1mo"),
            ("2024-07-01T13:00:00", "2025-07-02T13:00:00", "P1Y1D", "1y 1d"),
            ("2024-07-01T13:00:00", "2024-08-02T13:00:00", "P1M1D", "1mo 1d"),
            # 3x date changes
            ("2024-07-01", "2025-08-02", "P1Y1M1D", "1y 1mo 1d"),
            ("2024-07-01T13:00:00", "2025-08-02T13:00:00", "P1Y1M1D", "1y 1mo 1d"),
            # 1x time change
            ("13:00:00", "14:00:00", "PT1H", "1h"),
            ("13:00:00", "13:01:00", "PT1M", "1m"),
            ("13:00:00", "13:00:01", "PT1S", "1s"),
            ("2024-07-01T13:00:00", "2024-07-01T14:00:00", "PT1H", "1h"),
            ("2024-07-01T13:00:00", "2024-07-01T13:01:00", "PT1M", "1m"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01", "PT1S", "1s"),
            # 2x time changes
            ("13:00:00", "14:01:00", "PT1H1M", "1h 1m"),
            ("13:00:00", "14:00:01", "PT1H1S", "1h 1s"),
            ("13:00:00", "13:01:01", "PT1M1S", "1m 1s"),
            ("2024-07-01T13:00:00", "2024-07-01T14:01:00", "PT1H1M", "1h 1m"),
            ("2024-07-01T13:00:00", "2024-07-01T14:00:01", "PT1H1S", "1h 1s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:01:01", "PT1M1S", "1m 1s"),
            # 3x time changes
            ("13:00:00", "14:01:01", "PT1H1M1S", "1h 1m 1s"),
            ("2024-07-01T13:00:00", "2024-07-01T14:01:01", "PT1H1M1S", "1h 1m 1s"),
            # 1x date time + 3x time changes
            ("2024-07-01T13:00:00", "2025-07-01T14:01:01", "P1YT1H1M1S", "1y 1h 1m 1s"),
            (
                "2024-07-01T13:00:00",
                "2024-08-01T14:01:01",
                "P1MT1H1M1S",
                "1mo 1h 1m 1s",
            ),
            ("2024-07-01T13:00:00", "2024-07-02T14:01:01", "P1DT1H1M1S", "1d 1h 1m 1s"),
            # 2x date times + 3x time changes
            (
                "2024-07-01T13:00:00",
                "2025-08-01T14:01:01",
                "P1Y1MT1H1M1S",
                "1y 1mo 1h 1m 1s",
            ),
            (
                "2024-07-01T13:00:00",
                "2025-07-02T14:01:01",
                "P1Y1DT1H1M1S",
                "1y 1d 1h 1m 1s",
            ),
            (
                "2024-07-01T13:00:00",
                "2024-08-02T14:01:01",
                "P1M1DT1H1M1S",
                "1mo 1d 1h 1m 1s",
            ),
            # 3x date times + 3x time changes
            (
                "2024-07-01T13:00:00",
                "2025-08-02T14:01:01",
                "P1Y1M1DT1H1M1S",
                "1y 1mo 1d 1h 1m 1s",
            ),
            # microseconds
            ("2024-07-01T13:00:00.10Z", "2024-07-01T13:00:00.20Z", "PT0.1S", "0.1s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00.5", "PT0.5S", "0.5s"),
            ("2024-07-01T13:00:00", "2024-07-02T13:00:00.5", "P1DT0.5S", "1d 0.5s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00.123", "PT0.123S", "0.123s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01.123", "PT1.123S", "1.123s"),
            (
                "2024-07-01T13:00:00",
                "2024-07-01T13:01:00.123",
                "PT1M0.123S",
                "1m 0.123s",
            ),
            (
                "2024-07-01T10:11:30.123456+00:00",
                "2024-07-01T10:11:40.246801+00:00",
                "PT10.123345S",
                "10.123345s",
            ),
            #
            ("2024-07-01T13:00:00", "2024-07-02T14:00:00", "P1DT1H", "1d 1h"),
            ("2024-07-01T13:00:00", "2024-07-02T15:15:00", "P1DT2H15M", "1d 2h 15m"),
            (
                "2024-07-01T13:00:00",
                "2024-07-02T15:15:30",
                "P1DT2H15M30S",
                "1d 2h 15m 30s",
            ),
            (
                "2020-04-06T15:00:07Z",
                "2021-07-28T19:18:02+00:00",
                "P1Y3M22DT4H17M55S",
                "1y 3mo 22d 4h 17m 55s",
            ),
            (
                "2021-07-28T19:18:02+01:00",
                "2020-04-06T15:00:07+01:00",
                "P1Y3M22DT4H17M55S",
                "1y 3mo 22d 4h 17m 55s",
            ),
            ("2024-07-01T13:00:00+01:00", "2024-07-01T13:00:00+02:00", "PT1H", "1h"),
            ("2024-07-01T13:00:00+02:00", "2024-07-01T13:00:00+01:00", "PT1H", "1h"),
        ],
    )
    def test_as_default_extended(self, start: str, end: str, iso: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.is_zero is False
        assert result.as_iso() == iso
        assert result.as_default() == expected

    def test_as_compact_days(self):
        start = dt.datetime(2024, 7, 1, 13, 0, 0)
        end = dt.datetime(2025, 7, 1, 14, 1, 1)
        result = tt.ext.Duration(start, end)
        assert result.as_compact_days() == "365d 1h 1m 1s"

    @pytest.mark.parametrize(
        "start, end, iso, expected",
        [
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01", "PT1S", "1s"),
            (
                "2024-07-01T13:00:00",
                "2025-08-02T14:01:01",
                "P1Y1M1DT1H1M1S",
                "397d 1h 1m 1s",
            ),
            (
                "2024-07-01T13:00:00+00:00",
                "2024-07-03T23:17:36+00:00",
                "P2DT10H17M36S",
                "2d 10h 17m 36s",
            ),
            (
                "2024-07-01T13:00:00+00:00",
                "2024-07-04T13:02:00+00:00",
                "P3DT2M",
                "3d 2m",
            ),
            ("2024-07-01", "2025-08-02", "P1Y1M1D", "397d"),
            # microseconds
            ("2024-07-01T13:00:00.10Z", "2024-07-01T13:00:00.20Z", "PT0.1S", "0.1s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00.5", "PT0.5S", "0.5s"),
            ("2024-07-01T13:00:00", "2024-07-02T13:00:00.5", "P1DT0.5S", "1d 0.5s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00.123", "PT0.123S", "0.123s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01.123", "PT1.123S", "1.123s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:01:00.12", "PT1M0.12S", "1m 0.12s"),
        ],
    )
    def test_compact_days_extended(self, start: str, end: str, iso: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.is_zero is False
        assert result.as_iso() == iso
        assert result.as_compact_days() == expected

    def test_as_compact_weeks(self):
        start = dt.datetime(2024, 7, 1, 13, 0, 0)
        end = dt.datetime(2025, 7, 9, 14, 1, 1)
        result = tt.ext.Duration(start, end)
        assert result.as_compact_weeks() == "1y 1w 1d 1h 1m 1s"

    @pytest.mark.parametrize(
        "start, end, iso, expected",
        [
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01", "PT1S", "1s"),
            (
                "2024-07-01T13:00:00",
                "2025-08-02T14:01:01",
                "P1Y1M1DT1H1M1S",
                "1y 1mo 1d 1h 1m 1s",
            ),
            (
                "2024-07-01T13:00:00+00:00",
                "2025-07-09T14:01:01+00:00",
                "P1Y8DT1H1M1S",
                "1y 1w 1d 1h 1m 1s",
            ),
            (
                "2024-07-01T13:00:00+00:00",
                "2025-07-08T14:01:01+00:00",
                "P1Y7DT1H1M1S",
                "1y 1w 1h 1m 1s",
            ),
            (
                "2024-07-01T13:00:00+00:00",
                "2025-07-07T14:01:01+00:00",
                "P1Y6DT1H1M1S",
                "1y 6d 1h 1m 1s",
            ),
            # microseconds
            ("2024-07-01T13:00:00.10Z", "2024-07-01T13:00:00.20Z", "PT0.1S", "0.1s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00.5", "PT0.5S", "0.5s"),
            ("2024-07-01T13:00:00", "2024-07-02T13:00:00.5", "P1DT0.5S", "1d 0.5s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:00.123", "PT0.123S", "0.123s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01.123", "PT1.123S", "1.123s"),
            ("2024-07-01T13:00:00", "2024-07-01T13:01:00.12", "PT1M0.12S", "1m 0.12s"),
        ],
    )
    def test_compact_weeks_ext(self, start: str, end: str, iso: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.is_zero is False
        assert result.as_iso() == iso
        assert result.as_compact_weeks() == expected

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            (
                dt.datetime(2024, 7, 1, 13, 0, 0),
                dt.datetime(2025, 7, 1, 14, 1, 1),
                "P1YT1H1M1S",
            ),
            (
                dt.datetime(2024, 7, 1, 13, 0, 0),
                dt.datetime(2025, 7, 9, 14, 1, 1),
                "P1Y8DT1H1M1S",
            ),
        ],
    )
    def test_as_iso(self, start: dt.datetime, end: dt.datetime, expected: str):
        result = tt.ext.Duration(start, end)
        assert result.as_iso() == expected

    def test_as_total_seconds(self):
        start = dt.datetime(2024, 7, 1, 13, 0, 0)
        end = dt.datetime(2025, 7, 1, 14, 1, 1)
        result = tt.ext.Duration(start, end)
        formatted = result.as_total_seconds()
        assert formatted.endswith("s")
        # numeric part matches int(round(total_seconds))
        numeric = int(formatted[:-1].replace("_", ""))
        assert numeric == int(round(result.total_seconds))

    @pytest.mark.parametrize(
        "start, end, iso, expected",
        [
            ("2024-07-01T13:00:00", "2024-07-01T13:00:01", "PT1S", "1s"),
            ("2024-07-01T13:00:00", "2024-07-01T14:01:01", "PT1H1M1S", "3_661s"),
        ],
    )
    def test_total_secs_extended(self, start: str, end: str, iso: str, expected: str):
        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.is_zero is False
        assert result.as_iso() == iso
        assert result.as_total_seconds() == expected

    def test_as_custom(self):
        start = dt.datetime(2024, 7, 1, 13, 0, 0)
        end = dt.datetime(2025, 7, 1, 14, 1, 1)
        dur = tt.ext.Duration(start, end)
        result = dur.as_custom(lambda x: f"{x.years}y {x.months}mo {x.days}d")
        assert result == "1y 0mo 0d"

    @pytest.mark.parametrize(
        "start, end, iso, expected",
        [
            (
                "2024-07-01T13:00:00",
                "2025-07-01T14:01:00",
                "P1YT1H1M",
                "1 year, 0 months, 0 days, 1 hour, 1 minute, 0 seconds",
            ),
            (
                "2024-07-01T13:00:00",
                "2025-08-02T14:01:01",
                "P1Y1M1DT1H1M1S",
                "1 year, 1 month, 1 day, 1 hour, 1 minute, 1 second",
            ),
        ],
    )
    def test_custom(self, start: str, end: str, iso: str, expected: str):
        def show_all(d: tt.ext.Duration) -> str:
            def multiplier(value: int | float) -> str:
                return "" if value == 1 else "s"

            return ", ".join(
                [
                    f"{d.years} year{multiplier(d.years)}",
                    f"{d.months} month{multiplier(d.months)}",
                    f"{d.days} day{multiplier(d.days)}",
                    f"{d.hours} hour{multiplier(d.hours)}",
                    f"{d.minutes} minute{multiplier(d.minutes)}",
                    f"{d.formatted_seconds} second{multiplier(d.seconds)}",
                ]
            )

        result = tt.ext.Duration(start, end)
        assert isinstance(result, tt.ext.Duration)
        assert result.is_zero is False
        assert result.as_iso() == iso
        assert result.as_custom(formatter=show_all) == expected


class TestDateSub:
    def test_datesub_official_docs(self):
        date_time_values = [
            ("1992-09-30 23:59:59", "1992-10-01 01:58:00", "hour", 1),
            ("1992-09-30T23:59:59.012345", "1992-10-01T01:58:00.123456", "hour", 1),
            (
                dt.datetime(1992, 9, 30, 23, 59, 59),
                dt.datetime(1992, 10, 1, 1, 58, 00),
                "hour",
                1,
            ),
            ("1992-09-30 23:59:59", "1992-10-01 01:58:00", "min", 118),
            ("1992-09-30 23:59:59", "1992-10-01 01:58:00", "sec", 7081),
        ]
        for start, end, part, expected in date_time_values:
            result = tt.ext.datesub(part, start, end)
            assert result == expected

        time_values = [
            ("01:02:03", "06:01:03", "hour", 4),
            (dt.time(1, 2, 3), dt.time(6, 1, 3), "hour", 4),
        ]
        for start, end, part, expected in time_values:
            result = tt.ext.datesub(part, start, end)
            assert result == expected

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            ("ref_date", "ref_date", 0),
            #
            ("2024-01-01", "ref_date", 0),
            ("ref_date", "2024-01-01", 0),
            #
            ("2023-12-31", "ref_date", 0),
            ("ref_date", "2023-12-31", 0),
            #
            ("ref_date", "2024-12-31", 0),
            ("2024-12-31", "ref_date", 0),
            #
            ("ref_date", "2025-01-01", 0),
            ("2025-01-01", "ref_date", 0),
            #
            ("2023-06-30", "ref_date", 1),
            ("2023-07-01", "ref_date", 1),
            ("2023-07-02", "ref_date", 0),
            #
            ("ref_date", "2023-06-30", -1),
            ("ref_date", "2023-07-01", -1),
            ("ref_date", "2023-07-02", 0),
            #
            ("ref_date", "2025-06-30", 0),
            ("ref_date", "2025-07-01", 1),
            ("ref_date", "2025-07-02", 1),
            #
            ("2025-06-30", "ref_date", 0),
            ("2025-07-01", "ref_date", -1),
            ("2025-07-02", "ref_date", -1),
            #
            ("2022-06-30", "ref_date", 2),
            ("2022-07-01", "ref_date", 2),
            ("2022-07-02", "ref_date", 1),
            #
            ("ref_date", "2026-06-30", 1),
            ("ref_date", "2026-07-01", 2),
            ("ref_date", "2026-07-02", 2),
            #
            ("1970-01-01", "ref_date", 54),
        ],
    )
    def test_datesub__year(self, get_ref_date, start: str, end: str, expected: int):
        for cast_func in self.cast_funcs():
            start = cast_func(get_ref_date(start))
            end = cast_func(get_ref_date(end))
            for part in ("year", "years", "y", "yr", "yrs"):
                result = tt.ext.datesub(part, start, end)
                assert result == expected

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            ("ref_date", "ref_date", 0),
            #
            ("2024-06-30", "ref_date", 0),
            ("ref_date", "2024-06-30", 0),
            #
            ("ref_date", "2024-07-02", 0),
            ("2024-07-02", "ref_date", 0),
            #
            ("ref_date", "2024-07-07", 0),
            ("2024-07-07", "ref_date", 0),
            #
            ("2024-01-01", "ref_date", 6),
            ("ref_date", "2024-01-01", -6),
            #
            ("2023-12-31", "ref_date", 6),
            ("ref_date", "2023-12-31", -6),
            #
            ("ref_date", "2024-12-31", 5),
            ("2024-12-31", "ref_date", -5),
            #
            ("ref_date", "2025-01-01", 6),
            ("2025-01-01", "ref_date", -6),
            #
            ("2023-06-30", "ref_date", 12),
            ("2023-07-01", "ref_date", 12),
            ("2023-07-02", "ref_date", 11),
            #
            ("ref_date", "2023-06-30", -12),
            ("ref_date", "2023-07-01", -12),
            ("ref_date", "2023-07-02", -11),
            #
            ("ref_date", "2025-06-30", 11),
            ("ref_date", "2025-07-01", 12),
            ("ref_date", "2025-07-02", 12),
            #
            ("2025-06-30", "ref_date", -11),
            ("2025-07-01", "ref_date", -12),
            ("2025-07-02", "ref_date", -12),
            #
            ("2022-06-30", "ref_date", 24),
            ("2022-07-01", "ref_date", 24),
            ("2022-07-02", "ref_date", 23),
            #
            ("ref_date", "2026-06-30", 23),
            ("ref_date", "2026-07-01", 24),
            ("ref_date", "2026-07-02", 24),
            #
            ("1970-01-01", "ref_date", 654),
        ],
    )
    def test_datesub__month(self, get_ref_date, start: str, end: str, expected: int):
        for cast_func in self.cast_funcs():
            start = cast_func(get_ref_date(start))
            end = cast_func(get_ref_date(end))
            for part in ("month", "months", "mon", "mons"):
                result = tt.ext.datesub(part, start, end)
                assert result == expected

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            ("ref_date", "ref_date", 0),
            #
            ("2024-06-30", "ref_date", 1),
            ("ref_date", "2024-06-30", -1),
            #
            ("ref_date", "2024-07-02", 1),
            ("2024-07-02", "ref_date", -1),
            #
            ("ref_date", "2024-07-07", 6),
            ("2024-07-07", "ref_date", -6),
            #
            ("2024-01-01", "ref_date", 182),
            ("ref_date", "2024-01-01", -182),
            #
            ("2023-12-31", "ref_date", 183),
            ("ref_date", "2023-12-31", -183),
            #
            ("ref_date", "2024-12-31", 183),
            ("2024-12-31", "ref_date", -183),
            #
            ("ref_date", "2025-01-01", 184),
            ("2025-01-01", "ref_date", -184),
            #
            ("2023-06-30", "ref_date", 367),
            ("2023-07-01", "ref_date", 366),
            ("2023-07-02", "ref_date", 365),
            #
            ("ref_date", "2023-06-30", -367),
            ("ref_date", "2023-07-01", -366),
            ("ref_date", "2023-07-02", -365),
            #
            ("ref_date", "2025-06-30", 364),
            ("ref_date", "2025-07-01", 365),
            ("ref_date", "2025-07-02", 366),
            #
            ("2025-06-30", "ref_date", -364),
            ("2025-07-01", "ref_date", -365),
            ("2025-07-02", "ref_date", -366),
            #
            ("2022-06-30", "ref_date", 732),
            ("2022-07-01", "ref_date", 731),
            ("2022-07-02", "ref_date", 730),
            #
            ("ref_date", "2026-06-30", 729),
            ("ref_date", "2026-07-01", 730),
            ("ref_date", "2026-07-02", 731),
            #
            ("1970-01-01", "ref_date", 19_905),
        ],
    )
    def test_datesub__day(self, get_ref_date, start: str, end: str, expected: int):
        for cast_func in self.cast_funcs():
            start = cast_func(get_ref_date(start))
            end = cast_func(get_ref_date(end))
            for part in ("day", "days", "d", "dayofmonth"):
                result = tt.ext.datesub(part, start, end)
                assert result == expected

    @staticmethod
    def cast_funcs() -> tuple[Callable[[str], str | dt.date | dt.datetime]]:
        return (
            tt.ext.parse,
            lambda x: x,
            lambda x: dt.datetime.combine(tt.ext.parse(x), dt.datetime.min.time()),
        )

    @pytest.fixture(scope="class")
    def get_ref_date(self, request: pytest.FixtureRequest) -> Callable[[str], str]:
        def inner(value: str) -> str:
            return request.getfixturevalue("ref_date") if value == "ref_date" else value

        return inner

    @pytest.fixture(scope="class")
    def ref_date(self) -> str:
        return "2024-07-01"


class TestExtendedDateTimeParsing:
    @pytest.mark.parametrize(
        "value",
        [
            "March 3rd, 2020 5:30 PM",
            "Mar 3 2020 05:30 PM",
            "3 March 2020 17:30:45",
        ],
    )
    def test_stdlib_parse_rejects_natural_language(self, value: str):
        with pytest.raises(ValueError):
            tt.stdlib.parse(value)

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("2024-07-01T23:59:59", dt.datetime(2024, 7, 1, 23, 59, 59)),
            ("March 3rd, 2020 5:30 PM", dt.datetime(2020, 3, 3, 17, 30)),
            ("Mar 3 2020 05:30 PM", dt.datetime(2020, 3, 3, 17, 30)),
            ("3 March 2020 17:30:45", dt.datetime(2020, 3, 3, 17, 30, 45)),
            ("March 3, 2020", dt.datetime(2020, 3, 3, 0, 0)),
            ("March 3", dt.datetime(1900, 3, 3, 0, 0)),
        ],
    )
    def test_extended_parse(self, value: str, expected: dt.datetime):
        assert tt.ext.parse(value) == expected


class TestOffset:
    @pytest.mark.parametrize(
        "unit",
        [
            "microseconds",
            "seconds",
            "minutes",
            "hours",
            "days",
            "weeks",
            "months",
            "quarter",
            "years",
            "decade",
        ],
    )
    def test_zero_offset(self, unit: str):
        ref_dt = dt.datetime(2020, 1, 15, 0, 0, 0)
        result = tt.ext.offset(ref_dt, 0, unit)
        assert result == dt.datetime(2020, 1, 15, 0, 0, 0)

    @pytest.mark.parametrize(
        "unit, value, expected",
        [
            # add
            ("day", 1, dt.datetime(2020, 1, 16, 0, 0)),
            ("days", 15, dt.datetime(2020, 1, 30, 0, 0)),
            ("days", 16, dt.datetime(2020, 1, 31, 0, 0)),
            ("days", 365, dt.datetime(2021, 1, 14, 0, 0)),
            ("weeks", 3, dt.datetime(2020, 2, 5, 0, 0)),
            ("month", 1, dt.datetime(2020, 2, 15, 0, 0)),
            ("years", 2, dt.datetime(2022, 1, 15, 0, 0)),
            ("decade", 1, dt.datetime(2030, 1, 15, 0, 0)),
            ("quarter", 7, dt.datetime(2021, 10, 15, 0, 0)),
            # sub
            ("day", -1, dt.datetime(2020, 1, 14, 0, 0)),
            ("day", -14, dt.datetime(2020, 1, 1, 0, 0)),
            ("days", -15, dt.datetime(2019, 12, 31, 0, 0)),
            ("days", -365, dt.datetime(2019, 1, 15, 0, 0)),
            ("weeks", -3, dt.datetime(2019, 12, 25, 0, 0)),
            ("month", -1, dt.datetime(2019, 12, 15, 0, 0)),
            ("years", -2, dt.datetime(2018, 1, 15, 0, 0)),
            ("decade", -1, dt.datetime(2010, 1, 15, 0, 0)),
            ("quarter", -7, dt.datetime(2018, 4, 15, 0, 0)),
        ],
    )
    def test_offset(self, unit: str, value: int, expected: dt.datetime):
        ref_dt = dt.datetime(2020, 1, 15, 0, 0, 0)
        result = tt.ext.offset(ref_dt, value, unit)
        assert result == expected

    @pytest.mark.parametrize(
        "unit, value",
        [
            ("days", 3),
            ("days", -1),
            ("weeks", 2),
            ("hours", 5),
            ("minutes", 90),
            ("seconds", 30),
            ("microseconds", 1),
        ],
    )
    def test_timedelta_units_with_datetime(self, unit: str, value: int):
        ref_dt = dt.datetime(2020, 1, 1, 12, 0, 0)
        expected = ref_dt + dt.timedelta(**{unit: value})
        assert tt.ext.offset(ref_dt, value, unit) == expected

    @pytest.mark.parametrize(
        "reference, expected",
        [
            ("2020-01-01T12:00:00", dt.datetime(2020, 1, 1, 12, 0, 0)),
            ("2020-01-01", dt.datetime(2020, 1, 1, 0, 0, 0)),
            (dt.date(2020, 1, 2), dt.datetime(2020, 1, 2, 0, 0, 0)),
        ],
    )
    def test_string_and_date_inputs(
        self,
        reference: tt.stdlib.DateTimeLike,
        expected: dt.datetime,
    ):
        assert tt.ext.offset(reference, 0, "days") == expected

    def test_unit_case_and_plural_handling(self):
        ref_dt = dt.datetime(2021, 6, 1, 8, 0, 0)
        assert tt.ext.offset(ref_dt, 1, "Days") == ref_dt + dt.timedelta(days=1)
        assert tt.ext.offset(ref_dt, 2, "  HOURS  ") == ref_dt + dt.timedelta(hours=2)
        assert tt.ext.offset(ref_dt, -3, "MiNuTeS") == ref_dt + dt.timedelta(minutes=-3)

    def test_invalid_unit_raises_value_error(self):
        with pytest.raises(duckdb.ConversionException):
            tt.ext.offset(dt.datetime.now(), 1, "bad_value")
