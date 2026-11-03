import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMPILER = ROOT / "compiler.py"
VALID_DIR = ROOT / "tests" / "valid"
INVALID_DIR = ROOT / "tests" / "invalid"


def run_compiler(source_path, ast=False, output_path=None, optimize=False):
    command = [sys.executable, str(COMPILER)]

    if optimize:
        command.append("--optimize")

    if ast:
        command.append("--ast")

    if output_path is not None:
        command.extend(["-o", str(output_path)])

    command.append(str(source_path))

    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )


def run_ast_test(source_path):
    expected_path = source_path.with_suffix(".ast")

    if not expected_path.exists():
        return False, f"missing expected file: {expected_path.name}"

    expected = expected_path.read_text().rstrip("\n")
    result = run_compiler(source_path, ast=True)
    actual = result.stdout.rstrip("\n")

    if (
        result.returncode == 0
        and result.stderr == ""
        and actual == expected
    ):
        return True, ""

    return False, (
        f"exit code: {result.returncode}\n"
        f"expected AST:\n{expected}\n"
        f"actual AST:\n{actual}\n"
        f"stderr:\n{result.stderr}"
    )


def run_end_to_end_test(source_path, optimize=False):
    expected_path = source_path.with_suffix(".expected")
    input_path = source_path.with_suffix(".in")

    if not expected_path.exists():
        return False, f"missing expected file: {expected_path.name}"

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        ir_path = directory / "program.ll"
        executable_path = directory / "program"

        compilation = run_compiler(
            source_path,
            output_path=ir_path,
            optimize=optimize,
        )

        if compilation.returncode != 0:
            return False, (
                f"compiler failed:\n{compilation.stderr}"
            )

        clang = subprocess.run(
            ["clang", str(ir_path), "-o", str(executable_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )

        if clang.returncode != 0:
            return False, f"clang failed:\n{clang.stderr}"

        input_data = input_path.read_bytes() if input_path.exists() else b""

        execution = subprocess.run(
            [str(executable_path)],
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        expected = expected_path.read_bytes()
        actual = execution.stdout

        if execution.returncode == 0 and actual == expected:
            return True, ""

        return False, (
            f"exit code: {execution.returncode}\n"
            f"expected output: {expected!r}\n"
            f"actual output: {actual!r}\n"
            f"stderr: {execution.stderr.decode(errors='replace')}"
        )


def run_valid_tests():
    passed = 0
    total = 0
    end_to_end = 0
    input_tests = 0

    print("VALID TESTS")

    for source_path in sorted(VALID_DIR.glob("*.src")):
        total += 1
        name = source_path.stem

        if source_path.with_suffix(".expected").exists():
            end_to_end += 1
            if source_path.with_suffix(".in").exists():
                input_tests += 1
            success, details = run_end_to_end_test(source_path)
        else:
            success, details = run_ast_test(source_path)

        if success:
            passed += 1
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name}")
            print(details)

    return passed, total, end_to_end, input_tests


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
            print(f"  expected error: {expected!r}")
            print(f"  actual error: {actual!r}")
            if result.stdout:
                print(f"  unexpected stdout: {result.stdout!r}")

    return passed, total



def run_program_tests():
    print("\nINTERACTIVE PROGRAM TESTS")

    source_path = ROOT / "programs" / "traffic_checker.txt"
    passed = 0
    total = 0

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        ir_path = directory / "traffic_checker.ll"
        object_path = directory / "traffic_checker.o"
        executable_path = directory / "traffic_checker"

        compilation = run_compiler(source_path, output_path=ir_path)

        if compilation.returncode != 0:
            print(f"[FAIL] program compilation: {compilation.stderr}")
            return 0, 3

        llvm = subprocess.run(
            ["llc", "-filetype=obj", str(ir_path), "-o", str(object_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if llvm.returncode != 0:
            print(f"[FAIL] llc: {llvm.stderr}")
            return 0, 3

        linking = subprocess.run(
            ["clang", str(object_path), "-o", str(executable_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if linking.returncode != 0:
            print(f"[FAIL] clang: {linking.stderr}")
            return 0, 3

        for i in range(1, 4):
            total += 1

            input_path = ROOT / "programs" / f"traffic_checker_{i}.in"
            expected_path = ROOT / "programs" / f"traffic_checker_{i}.expected"

            if not input_path.exists() or not expected_path.exists():
                print(f"[FAIL] traffic_checker_{i}: missing session files")
                continue

            execution = subprocess.run(
                [str(executable_path)],
                input=input_path.read_bytes(),
                capture_output=True,
                timeout=10,
            )

            expected = expected_path.read_bytes()

            if execution.returncode == 0 and execution.stdout == expected:
                passed += 1
                print(f"[PASS] traffic_checker_{i}")
            else:
                print(f"[FAIL] traffic_checker_{i}")
                print(f"  expected: {expected!r}")
                print(f"  actual: {execution.stdout!r}")
                print(f"  stderr: {execution.stderr!r}")

    return passed, total


def main():
    valid_passed, valid_total, end_to_end, input_tests = run_valid_tests()
    invalid_passed, invalid_total = run_invalid_tests()
    program_passed, program_total = run_program_tests()

    passed = valid_passed + invalid_passed + program_passed
    total = valid_total + invalid_total + program_total

    print(f"\n{passed}/{total} tests passed")
    print(f"Valid programs: {valid_total}")
    print(f"Invalid programs: {invalid_total}")
    print(f"End-to-end tests: {end_to_end}")
    print(f"End-to-end tests with input: {input_tests}")
    print(f"Interactive program sessions: {program_total}")

    requirements_met = (
        valid_total >= 20
        and invalid_total >= 20
        and end_to_end >= 10
        and input_tests >= 1
    )

    if passed != total or not requirements_met:
        sys.exit(1)


if __name__ == "__main__":
    main()
