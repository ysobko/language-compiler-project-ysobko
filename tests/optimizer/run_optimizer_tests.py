from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).resolve().parent


def run(command, **kwargs):
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        **kwargs,
    )


passed = 0
sources = sorted(TESTS.glob("*.src"))

with tempfile.TemporaryDirectory() as temp_dir:
    temp = Path(temp_dir)

    for source in sources:
        name = source.stem
        base = source.with_suffix("")

        expected_ast = Path(str(base) + ".ast.expected").read_text()
        expected_output = Path(str(base) + ".expected").read_text()

        input_file = Path(str(base) + ".input")
        input_data = input_file.read_text() if input_file.exists() else ""

        try:
            ast = run([
                "python3",
                "compiler.py",
                str(source),
                "--optimize",
                "--ast",
            ]).stdout

            if ast != expected_ast:
                raise AssertionError("Optimized AST does not match")

            for optimized in (False, True):
                label = "optimized" if optimized else "normal"
                prefix = temp / f"{name}_{label}"

                command = [
                    "python3",
                    "compiler.py",
                    str(source),
                    "-o",
                    str(prefix) + ".ll",
                ]

                if optimized:
                    command.append("--optimize")

                run(command)

                run([
                    "llc",
                    "-filetype=obj",
                    str(prefix) + ".ll",
                    "-o",
                    str(prefix) + ".o",
                ])

                run([
                    "clang",
                    str(prefix) + ".o",
                    "-o",
                    str(prefix),
                ])

                result = run([str(prefix)], input=input_data)

                if result.stdout != expected_output:
                    raise AssertionError(
                        f"{label} output mismatch: "
                        f"expected {expected_output!r}, "
                        f"got {result.stdout!r}"
                    )

            passed += 1
            print(f"[PASS] {name}")

        except (subprocess.CalledProcessError, AssertionError) as error:
            print(f"[FAIL] {name}: {error}")

print(f"\n{passed}/{len(sources)} optimizer tests passed")

if passed != len(sources):
    raise SystemExit(1)
