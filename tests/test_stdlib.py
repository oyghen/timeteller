import datetime as dt
import itertools
import re
import zoneinfo
from collections.abc import Iterator
from typing import Any

import pytest
import time_machine

import timeteller as tt


class TestDateTimeParsing:
    @pytest.mark.parametrize(
        "value, expected",
        [
            # datetime
            (dt.datetime(2024, 7, 1), dt.datetime(2024, 7, 1, 0, 0, 0)),
            ("2024-07-01 00:00", dt.datetime(2024, 7, 1, 0, 0, 0)),
            ("2024-07-01 00:00:00", dt.datetime(2024, 7, 1, 0, 0, 0)),
            ("2024-07-01 12:00:00", dt.datetime(2024, 7, 1, 12, 0, 0)),
            ("20240701_120114", dt.datetime(2024, 7, 1, 12, 1, 14)),
            # date
            (dt.date(2024, 7, 1), dt.datetime(2024, 7, 1)),
            (dt.date(2024, 7, 1), dt.datetime(2024, 7, 1, 0, 0)),
            (dt.date(2024, 7, 1), dt.datetime(2024, 7, 1, 0, 0, 0)),
            ("2024-07-01", dt.datetime(2024, 7, 1)),
            ("2024-07-01", dt.datetime(2024, 7, 1)),
            ("20240701", dt.datetime(2024, 7, 1)),
            # time
            (dt.time(12, 30), dt.datetime(1900, 1, 1, 12, 30)),
            ("12:30", dt.datetime(1900, 1, 1, 12, 30)),
            ("12:30:00", dt.datetime(1900, 1, 1, 12, 30, 0)),
            ("T12:30:00", dt.datetime(1900, 1, 1, 12, 30, 0)),
            ("00:00", dt.datetime(1900, 1, 1, 0, 0)),
            # ISO 8601
            ("2024-07-01T00:00:00", dt.datetime(2024, 7, 1, 00)),
            ("2024-07-01T12:00:00", dt.datetime(2024, 7, 1, 12)),
            ("2024-07-01T23:59:59", dt.datetime(2024, 7, 1, 23, 59, 59)),
            # microseconds
            ("2024-07-01 12:00:00.123456", dt.datetime(2024, 7, 1, 12, 0, 0, 123456)),
            ("2024-07-02T13:01:01.123456", dt.datetime(2024, 7, 2, 13, 1, 1, 123456)),
            ("2024-07-02T13:01:01.1234567", dt.datetime(2024, 7, 2, 13, 1, 1, 123456)),
            ("2024-07-02T13:01:01.12345678", dt.datetime(2024, 7, 2, 13, 1, 1, 123456)),
            ("2024-07-02T13:01:01.012345678", dt.datetime(2024, 7, 2, 13, 1, 1, 12345)),
            ("2024-07-02T13:01:01.001234", dt.datetime(2024, 7, 2, 13, 1, 1, 1234)),
            ("12:15:00.123", dt.datetime(1900, 1, 1, 12, 15, 0, 123000)),
            ("T12:45:00.456", dt.datetime(1900, 1, 1, 12, 45, 0, 456000)),
            ("T12:45:00.010101", dt.datetime(1900, 1, 1, 12, 45, 0, 10101)),
            ("T12:45:00.101010", dt.datetime(1900, 1, 1, 12, 45, 0, 101010)),
            ("T12:45:00.012345", dt.datetime(1900, 1, 1, 12, 45, 0, 12345)),
            ("T12:45:00.123450", dt.datetime(1900, 1, 1, 12, 45, 0, 123450)),
            ("T12:45:00.000001", dt.datetime(1900, 1, 1, 12, 45, 0, 1)),
            ("T12:45:00.00001", dt.datetime(1900, 1, 1, 12, 45, 0, 10)),
        ],
    )
    def test_parse(self, value: tt.stdlib.DateTimeLike, expected: dt.datetime):
        result = tt.stdlib.parse(value)
        assert result.tzinfo is None
        assert result == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (
                "2024-07-01T11:22:33Z",
                dt.datetime(2024, 7, 1, 11, 22, 33, tzinfo=dt.UTC),
            ),
            (
                "2024-07-01T11:22:33+00:00",
                dt.datetime(2024, 7, 1, 11, 22, 33, tzinfo=dt.UTC),
            ),
            (
                "2024-07-01T11:22:33-00:00",
                dt.datetime(2024, 7, 1, 11, 22, 33, tzinfo=dt.UTC),
            ),
            (
                "2024-07-01T11:00:00+01:00",
                dt.datetime(2024, 7, 1, 11, tzinfo=dt.timezone(dt.timedelta(hours=1))),
            ),
            (
                "2024-07-01T11:00:00-01:00",
                dt.datetime(2024, 7, 1, 11, tzinfo=dt.timezone(dt.timedelta(hours=-1))),
            ),
            (
                "2024-07-01T11:00:00+01:00",
                dt.datetime(
                    2024, 7, 1, 11, tzinfo=dt.timezone(dt.timedelta(seconds=3600))
                ),
            ),
        ],
    )
    def test_tzinfo(self, value: tt.stdlib.DateTimeLike, expected: dt.datetime):
        result = tt.stdlib.parse(value)
        expected_tzname = (
            "UTC"
            if any(value.endswith(tz_suffix) for tz_suffix in ("Z", "+00:00", "-00:00"))
            else f"UTC{value[-6:]}"
        )
        assert result.tzinfo is not None
        assert result.tzname() == expected_tzname
        assert result == expected

    @pytest.mark.parametrize(
        "value_cet, value_dt",
        [
            ("2024-01-01T11:22:33+01:00", dt.datetime(2024, 1, 1, 11, 22, 33)),
            ("2024-07-01T11:22:33+01:00", dt.datetime(2024, 7, 1, 11, 22, 33)),
        ],
    )
    def test_tzinfo__cet(
        self,
        value_cet: tt.stdlib.DateTimeLike,
        value_dt: dt.datetime,
    ):
        try:
            result = tt.stdlib.parse(value_cet)
            expected = value_dt.replace(tzinfo=dt.timezone(dt.timedelta(seconds=3600)))
            assert result.tzinfo is not None
            assert result.tzname() == "UTC+01:00"
            assert result == expected
        except AssertionError:
            value_cest = value_cet.replace("+01:00", "+02:00")
            result = tt.stdlib.parse(value_cest)
            expected = value_dt.replace(tzinfo=dt.timezone(dt.timedelta(seconds=7200)))
            assert result.tzinfo is not None
            assert result.tzname() == "UTC+02:00"
            assert result == expected

    @pytest.mark.parametrize(
        "value, formats, expected",
        [
            (
                "2024/07/01  12.01.14",
                "%Y/%m/%d %H.%M.%S",
                dt.datetime(2024, 7, 1, 12, 1, 14),
            ),
            (
                "20240701_120114",
                "%Y%m%d_%H%M%S",
                dt.datetime(2024, 7, 1, 12, 1, 14),
            ),
        ],
    )
    def test_formats(
        self,
        value: tt.stdlib.DateTimeLike,
        formats: str,
        expected: dt.datetime,
    ):
        assert tt.stdlib.parse(value, formats) == expected

    @pytest.mark.parametrize("value", ["foo", "-"])
    def test_value_error(self, value: tt.stdlib.DateTimeLike):
        with pytest.raises(ValueError):
            tt.stdlib.parse(value)

    @pytest.mark.parametrize("value", [None, 0, 1.0])
    def test_type_error(self, value: tt.stdlib.DateTimeLike):
        with pytest.raises(TypeError):
            tt.stdlib.parse(value)

    def test_strptime_formats(self):
        items = tt.stdlib.STRPTIME_FORMATS
        assert isinstance(items, tuple)
        assert all(isinstance(item, str) for item in items)
        assert len(items) == 34


class TestNowAndTimestamp:
    # For example, on Windows w/o tzdata, available_timezones() returns empty set
    HAS_ZONE_NAMES = bool(zoneinfo.available_timezones())

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    def test_now_with_zone_name(self):
        dt_obj = tt.stdlib.now("UTC")
        assert isinstance(dt_obj, dt.datetime)
        assert dt_obj.tzinfo is not None
        assert dt_obj.utcoffset() == dt.timedelta(0)

    @pytest.mark.parametrize("timezone", [dt.UTC, dt.timezone.utc])  # noqa
    def test_now_with_tzinfo(self, timezone: dt.tzinfo):
        dt_obj = tt.stdlib.now(timezone)
        assert isinstance(dt_obj, dt.datetime)
        assert dt_obj.tzinfo is not None
        assert dt_obj.utcoffset() == dt.timedelta(0)

    def test_now_none_returns_aware_datetime(self):
        dt_obj = tt.stdlib.now()
        assert isinstance(dt_obj, dt.datetime)
        assert dt_obj.tzinfo is not None

    def test_timestamp_default_includes_offset_or_z(self):
        ts = tt.stdlib.timestamp()
        assert isinstance(ts, str)
        assert re.search(r"([+-]\d{2}:\d{2}|Z)$", ts)

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    def test_timestamp_with_format_matches_now(self):
        fmt = "%Y-%m-%d %H:%M"
        ts = tt.stdlib.timestamp("UTC", fmt=fmt)
        now_dt = tt.stdlib.now("UTC")
        assert ts == now_dt.strftime(fmt)

    def test_now_invalid_zone_raises_expected_error(self):
        expected_error = ValueError if self.HAS_ZONE_NAMES else LookupError
        with pytest.raises(expected_error):
            tt.stdlib.now("not/a/real/timezone")

    @pytest.fixture(scope="class")
    def seed(self) -> dt.datetime:
        """Return the seed for the time machine."""
        return dt.datetime(2024, 1, 1, 0, 0, 0)

    def test_timestamp_default_call(self, seed: dt.datetime):
        with time_machine.travel(seed):
            result = tt.stdlib.timestamp(dt.UTC)
            assert result == "2024-01-01T00:00:00+00:00"

    @pytest.mark.parametrize(
        "fmt, expected",
        [
            (None, "2024-01-01T00:00:00+00:00"),
            ("%Y-%m-%d %H:%M:%S", "2024-01-01 00:00:00"),
            ("%Y-%m-%d %H:%M:%S %Z", "2024-01-01 00:00:00 UTC"),
            ("%Y-%m-%d %H:%M:%S%z", "2024-01-01 00:00:00+0000"),
            ("%Y-%m-%d %H:%M:%S %Z%z", "2024-01-01 00:00:00 UTC+0000"),
            ("%Y%m%d-%H%M%S", "20240101-000000"),
            ("%H:%M:%S", "00:00:00"),
            ("%A, %d %B %Y %H:%M:%S", "Monday, 01 January 2024 00:00:00"),
        ],
    )
    def test_timestamp_with_utc(self, fmt: str, expected: str, seed: dt.datetime):
        with time_machine.travel(seed):
            result = tt.stdlib.timestamp(dt.UTC, fmt)
            assert result == expected

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    @pytest.mark.parametrize(
        "fmt, expected",
        [
            (None, "2024-01-01T01:00:00+01:00"),
            ("%Y-%m-%d %H:%M:%S", "2024-01-01 01:00:00"),
            ("%Y-%m-%d %H:%M:%S %Z", "2024-01-01 01:00:00 CET"),
            ("%Y-%m-%d %H:%M:%S%z", "2024-01-01 01:00:00+0100"),
            ("%Y-%m-%d %H:%M:%S %Z%z", "2024-01-01 01:00:00 CET+0100"),
            ("%Y%m%d-%H%M%S", "20240101-010000"),
            ("%H:%M:%S", "01:00:00"),
            ("%A, %d %B %Y %H:%M:%S", "Monday, 01 January 2024 01:00:00"),
        ],
    )
    def test_timestamp_with_cet(self, fmt: str, expected: str, seed: dt.datetime):
        with time_machine.travel(seed):
            result = tt.stdlib.timestamp("CET", fmt)
            assert result == expected

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    @pytest.mark.parametrize(
        "fmt, expected",
        [
            (None, "2023-12-31T14:00:00-10:00"),
            ("%Y-%m-%d %H:%M:%S", "2023-12-31 14:00:00"),
            ("%Y-%m-%d %H:%M:%S %Z", "2023-12-31 14:00:00 HST"),
            ("%Y-%m-%d %H:%M:%S%z", "2023-12-31 14:00:00-1000"),
            ("%Y-%m-%d %H:%M:%S %Z%z", "2023-12-31 14:00:00 HST-1000"),
            ("%Y%m%d-%H%M%S", "20231231-140000"),
            ("%H:%M:%S", "14:00:00"),
            ("%A, %d %B %Y %H:%M:%S", "Sunday, 31 December 2023 14:00:00"),
        ],
    )
    def test_timestamp_with_hawaii(self, fmt: str, expected: str, seed: dt.datetime):
        with time_machine.travel(seed):
            result = tt.stdlib.timestamp("US/Hawaii", fmt)
            assert result == expected

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    @pytest.mark.parametrize(
        "fmt, expected",
        [
            (None, "2024-01-01T09:00:00+09:00"),
            ("%Y-%m-%d %H:%M:%S", "2024-01-01 09:00:00"),
            ("%Y-%m-%d %H:%M:%S %Z", "2024-01-01 09:00:00 JST"),
            ("%Y-%m-%d %H:%M:%S%z", "2024-01-01 09:00:00+0900"),
            ("%Y-%m-%d %H:%M:%S %Z%z", "2024-01-01 09:00:00 JST+0900"),
            ("%Y%m%d-%H%M%S", "20240101-090000"),
            ("%H:%M:%S", "09:00:00"),
            ("%A, %d %B %Y %H:%M:%S", "Monday, 01 January 2024 09:00:00"),
        ],
    )
    def test_timestamp_with_tokyo(self, fmt: str, expected: str, seed: dt.datetime):
        with time_machine.travel(seed):
            result = tt.stdlib.timestamp("Asia/Tokyo", fmt)
            assert result == expected

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    @pytest.mark.parametrize(
        "timezone, fmt, expected_str, expected_dt",
        [
            (
                "UTC",
                None,
                "2024-01-01T00:00:00+00:00",
                dt.datetime(
                    2024, 1, 1, 0, 0, tzinfo=dt.timezone(dt.timedelta(seconds=0))
                ),
            ),
            (
                "CET",
                None,
                "2024-01-01T01:00:00+01:00",
                dt.datetime(
                    2024, 1, 1, 1, 0, tzinfo=dt.timezone(dt.timedelta(seconds=3600))
                ),
            ),
            (
                "US/Hawaii",
                None,
                "2023-12-31T14:00:00-10:00",
                dt.datetime(
                    2023,
                    12,
                    31,
                    14,
                    0,
                    tzinfo=dt.timezone(dt.timedelta(days=-1, seconds=50400)),
                ),
            ),
            (
                "Asia/Tokyo",
                None,
                "2024-01-01T09:00:00+09:00",
                dt.datetime(
                    2024,
                    1,
                    1,
                    9,
                    0,
                    tzinfo=dt.timezone(dt.timedelta(seconds=32400)),
                ),
            ),
        ],
    )
    def test_timestamp_to_datetime(
        self,
        timezone,
        fmt: str,
        expected_str: str,
        expected_dt: dt.datetime,
        seed: dt.datetime,
    ):
        with time_machine.travel(seed):
            result = tt.stdlib.timestamp(timezone, fmt)
            assert result == expected_str
            assert tt.stdlib.parse(result) == expected_dt


class TestIsoformat:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (dt.date(2024, 1, 1), "2024-01-01"),
            (dt.date(1999, 12, 31), "1999-12-31"),
        ],
    )
    def test_date_input(self, value: dt.date, expected: str):
        assert tt.stdlib.isoformat(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (dt.datetime(2024, 1, 1, 0, 0, 0), "2024-01-01"),
            (dt.datetime(2024, 1, 1, 0, 0, 0, 0), "2024-01-01"),
        ],
    )
    def test_datetime_midnight_naive(self, value: dt.datetime, expected: str):
        assert tt.stdlib.isoformat(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (dt.datetime(2024, 1, 1, 12, 0, 0), "2024-01-01T12:00:00"),
            (dt.datetime(2024, 1, 1, 0, 0, 1), "2024-01-01T00:00:01"),
            (dt.datetime(2024, 1, 1, 0, 0, 0, 1), "2024-01-01T00:00:00.000001"),
        ],
    )
    def test_datetime_non_midnight_naive(self, value: dt.datetime, expected: str):
        assert tt.stdlib.isoformat(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.UTC), "2024-01-01"),
            (
                dt.datetime(
                    2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=2))
                ),
                "2024-01-01",
            ),
        ],
    )
    def test_datetime_midnight_aware(self, value: dt.datetime, expected: str):
        assert tt.stdlib.isoformat(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (
                dt.datetime(2024, 1, 1, 8, 30, tzinfo=dt.UTC),
                "2024-01-01T08:30:00+00:00",
            ),
            (
                dt.datetime(
                    2024, 1, 1, 23, 59, 59, tzinfo=dt.timezone(dt.timedelta(hours=-5))
                ),
                "2024-01-01T23:59:59-05:00",
            ),
        ],
    )
    def test_datetime_non_midnight_aware(self, value: dt.datetime, expected: str):
        assert tt.stdlib.isoformat(value) == expected


class TestLastDay:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("2022-01-01", dt.datetime(2022, 1, 31)),
            ("2022-02-01", dt.datetime(2022, 2, 28)),
            ("2022-03-01", dt.datetime(2022, 3, 31)),
            ("2022-04-01", dt.datetime(2022, 4, 30)),
            ("2022-05-01", dt.datetime(2022, 5, 31)),
            ("2022-06-01", dt.datetime(2022, 6, 30)),
            ("2022-07-01", dt.datetime(2022, 7, 31)),
            ("2022-08-01", dt.datetime(2022, 8, 31)),
            ("2022-09-01", dt.datetime(2022, 9, 30)),
            ("2022-10-01", dt.datetime(2022, 10, 31)),
            ("2022-11-01", dt.datetime(2022, 11, 30)),
            ("2022-12-01", dt.datetime(2022, 12, 31)),
            ("1970-01-01", dt.datetime(1970, 1, 31)),
            ("1970-01-15", dt.datetime(1970, 1, 31)),
            ("1970-01-31", dt.datetime(1970, 1, 31)),
            ("2024-02-02", dt.datetime(2024, 2, 29)),  # leap year
            ("2020-02-02", dt.datetime(2020, 2, 29)),  # leap year
            ("2022-02-03", dt.datetime(2022, 2, 28)),
            ("2000-02-04", dt.datetime(2000, 2, 29)),  # leap year
            ("1900-02-05", dt.datetime(1900, 2, 28)),
            ("2012-02-27", dt.datetime(2012, 2, 29)),  # leap year
            ("2012-02-28", dt.datetime(2012, 2, 29)),  # leap year
            ("2012-02-29", dt.datetime(2012, 2, 29)),  # leap year
        ],
    )
    def test_last_day_string(self, value: str, expected: dt.datetime):
        assert tt.stdlib.last_day(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (dt.datetime(2023, 1, 15), dt.datetime(2023, 1, 31)),
            (dt.datetime(2023, 2, 10), dt.datetime(2023, 2, 28)),
            (dt.datetime(2024, 2, 1), dt.datetime(2024, 2, 29)),  # leap year
            (dt.datetime(2023, 4, 30), dt.datetime(2023, 4, 30)),
        ],
    )
    def test_last_day_datetime(self, value: dt.datetime, expected: dt.datetime):
        assert tt.stdlib.last_day(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (
                dt.datetime(2023, 1, 15, 12, 0, tzinfo=dt.UTC),
                dt.datetime(2023, 1, 31, 0, 0, tzinfo=dt.UTC),
            )
        ],
    )
    def test_last_day_timezone_aware(self, value: dt.datetime, expected: dt.datetime):
        assert tt.stdlib.last_day(value) == expected


class TestOffset:
    @pytest.mark.parametrize(
        "unit",
        [
            "weeks",
            "days",
            "hours",
            "minutes",
            "seconds",
            "microseconds",
            "milliseconds",
        ],
    )
    def test_zero_offset(self, unit: str):
        ref_dt = dt.datetime(2020, 1, 15, 0, 0, 0)
        result = tt.stdlib.offset(ref_dt, 0, unit)
        assert result == dt.datetime(2020, 1, 15, 0, 0, 0)

    @pytest.mark.parametrize(
        "unit, value, expected",
        [
            # add - date ahead
            ("weeks", 3, dt.datetime(2020, 2, 5, 0, 0)),
            ("days", 1, dt.datetime(2020, 1, 16, 0, 0)),
            ("days", 15, dt.datetime(2020, 1, 30, 0, 0)),
            ("days", 16, dt.datetime(2020, 1, 31, 0, 0)),
            ("days", 365, dt.datetime(2021, 1, 14, 0, 0)),
            ("hours", 2, dt.datetime(2020, 1, 15, 2, 0)),
            ("minutes", 30, dt.datetime(2020, 1, 15, 0, 30)),
            ("seconds", 45, dt.datetime(2020, 1, 15, 0, 0, 45)),
            ("microseconds", 500, dt.datetime(2020, 1, 15, 0, 0, 0, 500)),
            ("milliseconds", 1000, dt.datetime(2020, 1, 15, 0, 0, 1)),
            # sub - date ago
            ("weeks", -3, dt.datetime(2019, 12, 25, 0, 0)),
            ("days", -1, dt.datetime(2020, 1, 14, 0, 0)),
            ("days", -14, dt.datetime(2020, 1, 1, 0, 0)),
            ("days", -15, dt.datetime(2019, 12, 31, 0, 0)),
            ("days", -365, dt.datetime(2019, 1, 15, 0, 0)),
            ("hours", -2, dt.datetime(2020, 1, 14, 22, 0)),
            ("minutes", -30, dt.datetime(2020, 1, 14, 23, 30)),
            ("seconds", -45, dt.datetime(2020, 1, 14, 23, 59, 15)),
            ("microseconds", -500, dt.datetime(2020, 1, 14, 23, 59, 59, 999500)),
            ("milliseconds", -1000, dt.datetime(2020, 1, 14, 23, 59, 59, 0)),
        ],
    )
    def test_offset(self, unit: str, value: int, expected: dt.datetime):
        ref_dt = dt.datetime(2020, 1, 15, 0, 0, 0)
        result = tt.stdlib.offset(ref_dt, value, unit)
        assert result == expected

    @pytest.mark.parametrize(
        "value, reference, expected",
        [
            # same date as reference
            (0, dt.date(2022, 1, 1), dt.datetime(2022, 1, 1)),
            # add - date ahead
            (1, dt.date(2022, 1, 1), dt.datetime(2022, 1, 2)),
            (2, dt.date(2022, 1, 1), dt.datetime(2022, 1, 3)),
            (3, dt.date(2022, 1, 1), dt.datetime(2022, 1, 4)),
            (7, dt.date(2022, 8, 1), dt.datetime(2022, 8, 8)),
            (30, dt.date(2022, 8, 1), dt.datetime(2022, 8, 31)),
            (27, dt.date(2022, 2, 1), dt.datetime(2022, 2, 28)),
            (28, dt.date(2022, 2, 1), dt.datetime(2022, 3, 1)),
            (27, dt.date(2020, 2, 1), dt.datetime(2020, 2, 28)),
            (28, dt.date(2020, 2, 1), dt.datetime(2020, 2, 29)),
            (29, dt.date(2020, 2, 1), dt.datetime(2020, 3, 1)),
            # sub - date ago
            (-1, dt.date(2022, 1, 1), dt.datetime(2021, 12, 31)),
            (-2, dt.date(2022, 1, 1), dt.datetime(2021, 12, 30)),
            (-3, dt.date(2022, 1, 1), dt.datetime(2021, 12, 29)),
            (-7, dt.date(2022, 8, 1), dt.datetime(2022, 7, 25)),
            (-30, dt.date(2022, 8, 1), dt.datetime(2022, 7, 2)),
            (-27, dt.date(2022, 2, 1), dt.datetime(2022, 1, 5)),
            (-28, dt.date(2022, 2, 1), dt.datetime(2022, 1, 4)),
            (-27, dt.date(2020, 2, 1), dt.datetime(2020, 1, 5)),
            (-28, dt.date(2020, 2, 1), dt.datetime(2020, 1, 4)),
            (-29, dt.date(2020, 2, 1), dt.datetime(2020, 1, 3)),
        ],
    )
    def test_offset_date_type(
        self,
        value: int,
        reference: dt.date,
        expected: dt.datetime,
    ):
        result = tt.stdlib.offset(reference, value, "days")
        assert result == expected

    @pytest.mark.parametrize("value", ["1", 1.0, None, [], {}])
    def test_invalid_value_type(self, value: Any):
        with pytest.raises(TypeError, match="unsupported type .*; expected int"):
            tt.stdlib.offset("2020-01-15", value, "days")

    @pytest.mark.parametrize("unit", ["year", "month", "century", "", "Day"])
    def test_invalid_unit(self, unit: str):
        with pytest.raises(ValueError, match="invalid choice .*; expected a value .*"):
            tt.stdlib.offset("2020-01-15", 1, unit)


class TestCount:
    def test_count_forward(self):
        reference = dt.date(2022, 1, 1)
        seq = tt.stdlib.count(reference, 1, "days")
        result = list(itertools.islice(seq, 3))
        expected = [
            dt.datetime(2022, 1, 1),
            dt.datetime(2022, 1, 2),
            dt.datetime(2022, 1, 3),
        ]
        assert result == expected

    def test_count_backward(self):
        reference = dt.date(2022, 1, 1)
        seq = tt.stdlib.count(reference, -1, "days")
        result = list(itertools.islice(seq, 3))
        expected = [
            dt.datetime(2022, 1, 1),
            dt.datetime(2021, 12, 31),
            dt.datetime(2021, 12, 30),
        ]
        assert result == expected

    @pytest.mark.parametrize(
        "reference, value, unit, expected_first, expected_second",
        [
            (
                dt.datetime(2024, 1, 1, 0, 0),
                1,
                "days",
                dt.datetime(2024, 1, 1),
                dt.datetime(2024, 1, 2),
            ),
            (
                dt.datetime(2024, 1, 1, 12, 0),
                2,
                "hours",
                dt.datetime(2024, 1, 1, 12, 0),
                dt.datetime(2024, 1, 1, 14, 0),
            ),
            (
                dt.date(2024, 1, 1),
                1,
                "weeks",
                dt.datetime(2024, 1, 1),
                dt.datetime(2024, 1, 8),
            ),
        ],
    )
    def test_basic_progression(
        self,
        reference: tt.stdlib.DateTimeLike,
        value: int,
        unit: str,
        expected_first: dt.datetime,
        expected_second: dt.datetime,
    ) -> None:
        iterator = tt.stdlib.count(reference, value, unit)

        first = next(iterator)
        second = next(iterator)

        assert first == expected_first
        assert second == expected_second

    @pytest.mark.parametrize("value", [0, -1, -5])
    def test_zero_and_negative_steps(self, value: int) -> None:
        reference = dt.datetime(2024, 1, 1)
        iterator = tt.stdlib.count(reference, value, "days")

        first = next(iterator)
        second = next(iterator)

        assert first == reference
        assert second == reference + dt.timedelta(days=value)

    @pytest.mark.parametrize("unit", ["day", "month", "years", "foo", ""])
    def test_invalid_unit_raises_value_error(self, unit: str) -> None:
        with pytest.raises(ValueError):
            next(tt.stdlib.count(dt.datetime(2024, 1, 1), 1, unit))

    @pytest.mark.parametrize("value", [1.5, "1", None])
    def test_invalid_value_type_raises_type_error(self, value: Any) -> None:
        with pytest.raises(TypeError):
            next(tt.stdlib.count(dt.datetime(2024, 1, 1), value, "days"))

    def test_iterator_is_infinite(self) -> None:
        iterator = tt.stdlib.count(dt.datetime(2024, 1, 1), 1, "days")
        assert isinstance(iterator, Iterator)
        for _ in range(100):
            next(iterator)
        result = next(iterator)
        assert result == dt.datetime(2024, 4, 10)
