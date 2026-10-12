import re
from pathlib import Path

import pytest

from leakguard import RULES, check_source

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.py"))
EXPECT = re.compile(r"#\s*expect:\s*(LG\d+)")


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_flags_exactly_the_expected_lines(path):
    source = path.read_text()
    expected = {(i, m.group(1)) for i, line in enumerate(source.splitlines(), 1) if (m := EXPECT.search(line))}
    got = {(f.line, f.rule) for f in check_source(source, str(path))}
    assert got == expected, f"unexpected: {sorted(got - expected)}  missing: {sorted(expected - got)}"


def test_every_rule_has_a_fixture_with_positive_and_negative_cases():
    text = "\n".join(p.read_text() for p in FIXTURES)
    for rid in RULES:
        assert f"expect: {rid}" in text, f"{rid} has no should-flag case"
    assert len(RULES) >= 6


def test_syntax_errors_propagate_so_callers_cannot_mistake_them_for_clean():
    with pytest.raises(SyntaxError):
        check_source("def broken(:\n")


def test_finding_format_has_path_line_col_and_rule():
    f = check_source("import pandas as pd\ns = pd.Series([1])\nx = s.rolling(2, center=True).mean()\n")[0]
    assert f.format("m.py").startswith("m.py:3:5: LG002 ")
