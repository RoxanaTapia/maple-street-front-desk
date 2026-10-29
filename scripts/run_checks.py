"""Run the automatic checks from the project root.

With no arguments, every check runs. Pass a test file, or a file and class
such as tests/test_pages.py:PageListChecks, to run one area.
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CheckLoadError(Exception):
    """A requested check file or class could not be loaded."""


def _label(test):
    text = test.shortDescription()
    if text:
        return " ".join(text.split())
    name = getattr(test, "_testMethodName", str(test))
    if name.startswith("test_"):
        name = name[5:]
    return name.replace("_", " ").strip()


class SummaryResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.rows = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append((True, _label(test)))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.rows.append((False, _label(test)))

    def addError(self, test, err):
        super().addError(test, err)
        self.rows.append((False, _label(test)))


def _load_target(loader, target):
    file_part, separator, class_name = target.partition(":")
    path = Path(file_part)
    if not path.is_file():
        path = ROOT / file_part
    if not path.is_file():
        raise CheckLoadError(f"No check file at {file_part}.")
    module_name = "checks_" + path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CheckLoadError(f"Could not load {file_part}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if separator:
        if not class_name:
            raise CheckLoadError(f"Name the class after the colon in {target}.")
        try:
            return loader.loadTestsFromName(class_name, module)
        except AttributeError as error:
            raise CheckLoadError(f"No check class {class_name} in {file_part}.") from error
    return loader.loadTestsFromModule(module)


def _load(targets):
    loader = unittest.defaultTestLoader
    if not targets:
        return loader.discover(str(ROOT / "tests"))
    suite = unittest.TestSuite()
    for target in targets:
        suite.addTest(_load_target(loader, target))
    return suite


def _write_summary(rows):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = []
    for passed, label in rows:
        mark = "x" if passed else " "
        word = "Pass" if passed else "Fail"
        lines.append(f"- [{mark}] {word}. {label}")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    try:
        suite = _load(argv)
    except CheckLoadError as error:
        print(error, file=sys.stderr)
        return 1
    if suite.countTestCases() == 0:
        print("No checks found.", file=sys.stderr)
        return 1
    runner = unittest.TextTestRunner(verbosity=2, resultclass=SummaryResult)
    result = runner.run(suite)
    _write_summary(result.rows)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
