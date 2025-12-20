import timeteller


def main():
    result = timeteller.__name__
    expected = "timeteller"
    if result == expected:
        print("smoke test passed")
    else:
        raise RuntimeError("smoke test failed")


if __name__ == "__main__":
    main()
