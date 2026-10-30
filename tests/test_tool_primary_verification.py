import importlib.util
import sys
from pathlib import Path


def test_junit_counts_rejects_skipped_and_errors(tmp_path):
    benchmarks = Path(__file__).resolve().parents[1] / "benchmarks"
    sys.path.insert(0, str(benchmarks))
    try:
        spec = importlib.util.spec_from_file_location(
            "primary_verify_test", benchmarks / "tool_primary_verification.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path = tmp_path / "results.xml"
        path.write_text(
            "<testsuites><testsuite><testcase/><testcase><skipped/></testcase><testcase><error/></testcase><testcase><failure/></testcase></testsuite></testsuites>"
        )
        assert module.junit_counts(path) == {
            "tests": 4,
            "failure": 1,
            "error": 1,
            "skipped": 1,
        }
    finally:
        sys.path.remove(str(benchmarks))
