import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
COMPILER = ROOT / "compiler.py"
VALID_DIR = ROOT / "tests" / "valid"
INVALID_DIR = ROOT / "tests" / "invalid"


def run_compiler(source_path, ast=False):
    command = [
        sys.executable,
        str(COMPILER),
    ]

    if ast:
        command.append("--ast")

    with source_path.open("rb") as source:
        return subprocess.run(
            command,
            stdin=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


def run_valid_tests():
    passed = 0
    total = 0

    print("VALID TESTS")

    for source_path in sorted(VALID_DIR.glob("*.src")):
        total += 1

        name = source_path.stem
        expected_path = source_path.with_suffix(".ast")

        if not expected_path.exists():
            print(f"[FAIL] {name}")
            print(f"  missing expected file: {expected_path.name}")
            continue

        expected = expected_path.read_text().rstrip("\n")
        result = run_compiler(source_path, ast=True)
        actual = result.stdout.rstrip("\n")

        if (
            result.returncode == 0
            and result.stderr == ""
            and actual == expected
        ):
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            print(f"  exit code: {result.returncode}")

            if result.stderr:
                print("  stderr:")
                print(result.stderr.rstrip())

            if actual != expected:
                print("  expected AST:")
                print(expected)
                print("  actual AST:")
                print(actual)

    return passed, total


def run_invalid_tests():
    passed = 0
    total = 0

    print("\nINVALID TESTS")

    for source_path in sorted(INVALID_DIR.glob("*.src")):
        total += 1

        name = source_path.stem
        expected_path = source_path.with_suffix(".err")

        if not expected_path.exists():
            print(f"[FAIL] {name}")
            print(f"  missing expected file: {expected_path.name}")
            continue

        expected = expected_path.read_text().rstrip("\n")
        result = run_compiler(source_path)
        actual = result.stderr.rstrip("\n")

        if (
            result.returncode != 0
            and result.stdout == ""
            and actual == expected
        ):
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            print(f"  exit code: {result.returncode}")

            if result.stdout:
                print("  unexpected stdout:")
                print(result.stdout.rstrip())

            if actual != expected:
                print("  expected error:")
                print(expected)
                print("  actual error:")
                print(actual)

    return passed, total


def main():
    valid_passed, valid_total = run_valid_tests()
    invalid_passed, invalid_total = run_invalid_tests()

    passed = valid_passed + invalid_passed
    total = valid_total + invalid_total

    print(f"\n{passed}/{total} tests passed")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
