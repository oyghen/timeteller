<div align="center">

# timeteller-cli

[![GitHub](https://img.shields.io/badge/github-code-blue?label=GitHub)](https://github.com/oyghen/timeteller/tree/main/packages/timeteller-cli)
[![PyPI](https://img.shields.io/pypi/v/timeteller-cli?label=PyPI)](https://pypi.org/project/timeteller-cli)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://github.com/oyghen/timeteller/blob/main/LICENSE)
[![CI](https://github.com/oyghen/timeteller/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/oyghen/timeteller/actions/workflows/ci.yml)

</div>

```shell
uv tool install timeteller-cli
```

The `offset` command accepts fractional time-unit values:

```shell
timeteller offset 2024-01-01T12:00:00 add 5.5 hours
```

This adds 5 hours and 30 minutes, producing `2024-01-01T17:30:00`.
