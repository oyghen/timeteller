import datetime as dt
import re
import zoneinfo

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
        ],
    )
    def test_parse(self, value: tt.core.DateTimeLike, expected: dt.datetime):
        result = tt.core.parse(value)
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
    def test_tzinfo(self, value: tt.core.DateTimeLike, expected: dt.datetime):
        result = tt.core.parse(value)
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
        value_cet: tt.core.DateTimeLike,
        value_dt: dt.datetime,
    ):
        try:
            result = tt.core.parse(value_cet)
            expected = value_dt.replace(tzinfo=dt.timezone(dt.timedelta(seconds=3600)))
            assert result.tzinfo is not None
            assert result.tzname() == "UTC+01:00"
            assert result == expected
        except AssertionError:
            value_cest = value_cet.replace("+01:00", "+02:00")
            result = tt.core.parse(value_cest)
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
        value: tt.core.DateTimeLike,
        formats: str,
        expected: dt.datetime,
    ):
        assert tt.core.parse(value, formats) == expected

    @pytest.mark.parametrize("value", ["foo", "-"])
    def test_value_error(self, value: tt.core.DateTimeLike):
        with pytest.raises(ValueError):
            tt.core.parse(value)

    @pytest.mark.parametrize("value", [None, 0, 1.0])
    def test_type_error(self, value: tt.core.DateTimeLike):
        with pytest.raises(TypeError):
            tt.core.parse(value)

    def test_strptime_formats(self):
        items = tt.core.STRPTIME_FORMATS
        assert isinstance(items, tuple)
        assert all(isinstance(item, str) for item in items)
        assert len(items) == 34


class TestNowAndTimestamp:
    # For example, on Windows w/o tzdata, available_timezones() returns empty set
    HAS_ZONE_NAMES = bool(zoneinfo.available_timezones())

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    def test_now_with_zone_name(self):
        dt_obj = tt.core.now("UTC")
        assert isinstance(dt_obj, dt.datetime)
        assert dt_obj.tzinfo is not None
        assert dt_obj.utcoffset() == dt.timedelta(0)

    @pytest.mark.parametrize("timezone", [dt.UTC, dt.timezone.utc])  # noqa
    def test_now_with_tzinfo(self, timezone: dt.tzinfo):
        dt_obj = tt.core.now(timezone)
        assert isinstance(dt_obj, dt.datetime)
        assert dt_obj.tzinfo is not None
        assert dt_obj.utcoffset() == dt.timedelta(0)

    def test_now_none_returns_aware_datetime(self):
        dt_obj = tt.core.now()
        assert isinstance(dt_obj, dt.datetime)
        assert dt_obj.tzinfo is not None

    def test_timestamp_default_includes_offset_or_z(self):
        ts = tt.core.timestamp()
        assert isinstance(ts, str)
        assert re.search(r"([+-]\d{2}:\d{2}|Z)$", ts)

    @pytest.mark.skipif(not HAS_ZONE_NAMES, reason="no timezone names available")
    def test_timestamp_with_format_matches_now(self):
        fmt = "%Y-%m-%d %H:%M"
        ts = tt.core.timestamp("UTC", fmt=fmt)
        now_dt = tt.core.now("UTC")
        assert ts == now_dt.strftime(fmt)

    def test_now_invalid_zone_raises_expected_error(self):
        expected_error = ValueError if self.HAS_ZONE_NAMES else LookupError
        with pytest.raises(expected_error):
            tt.core.now("not/a/real/timezone")

    @pytest.fixture(scope="class")
    def seed(self) -> dt.datetime:
        """Return the seed for the time machine."""
        return dt.datetime(2024, 1, 1, 0, 0, 0)

    def test_timestamp_default_call(self, seed: dt.datetime):
        with time_machine.travel(seed):
            result = tt.core.timestamp(dt.UTC)
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
            result = tt.core.timestamp(dt.UTC, fmt)
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
            result = tt.core.timestamp("CET", fmt)
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
            result = tt.core.timestamp("US/Hawaii", fmt)
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
            result = tt.core.timestamp("Asia/Tokyo", fmt)
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
            result = tt.core.timestamp(timezone, fmt)
            assert result == expected_str
            assert tt.core.parse(result) == expected_dt
