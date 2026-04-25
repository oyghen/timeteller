import timeteller_cli


def main():
    result = timeteller_cli.__name__
    expected = "timeteller_cli"
    if result == expected:
        print(f"Smoke test for {timeteller_cli.__name__}: PASSED")
    else:
        raise RuntimeError(f"Smoke test for {timeteller_cli.__name__}: FAILED")


if __name__ == "__main__":
    main()
