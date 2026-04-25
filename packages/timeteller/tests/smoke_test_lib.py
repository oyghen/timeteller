import timeteller


def main() -> None:
    result = timeteller.__name__
    expected = "timeteller"
    if result == expected:
        print(f"Smoke test for {timeteller.__name__}: PASSED")
    else:
        raise RuntimeError(f"Smoke test for {timeteller.__name__}: FAILED")


if __name__ == "__main__":
    main()
