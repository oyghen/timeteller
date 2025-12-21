import datetime as dt

import pytest

import timeteller as tt


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
