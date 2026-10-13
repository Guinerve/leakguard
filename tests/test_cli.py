import json

from leakguard.cli import main, notebook_to_source


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_exit_code_and_output(tmp_path, capsys):
    bad = write(tmp_path, "bad.py", "import pandas as pd\ns = pd.Series([1])\nx = s.bfill()\n")
    assert main(["check", str(bad)]) == 1
    assert "LG004" in capsys.readouterr().out
    good = write(tmp_path, "good.py", "x = 1\n")
    assert main(["check", str(good)]) == 0


def test_json_format_and_select(tmp_path, capsys):
    p = write(tmp_path, "m.py", "import pandas as pd\ns = pd.Series([1])\na = s.bfill()\nb = s.rolling(2, center=True).mean()\n")
    main(["check", str(p), "--format", "json", "--select", "LG002"])
    out = json.loads(capsys.readouterr().out)
    assert [o["rule"] for o in out] == ["LG002"]


def test_directory_walk_skips_hidden_dirs(tmp_path, capsys):
    (tmp_path / ".venv").mkdir()
    write(tmp_path / ".venv", "x.py", "import pandas as pd\ns = pd.Series([1])\na = s.bfill()\n")
    write(tmp_path, "ok.py", "x = 1\n")
    assert main(["check", str(tmp_path)]) == 0


def test_notebook_support(tmp_path, capsys):
    nb = {"cells": [
        {"cell_type": "markdown", "source": ["# title"]},
        {"cell_type": "code", "source": ["%matplotlib inline\n", "import pandas as pd\n", "s = pd.Series([1])\n"]},
        {"cell_type": "code", "source": ["x = s.rolling(2, center=True).mean()"]},
    ]}
    p = write(tmp_path, "n.ipynb", json.dumps(nb))
    assert "%matplotlib" not in notebook_to_source(p.read_text())
    assert main(["check", str(p)]) == 1
    assert "LG002" in capsys.readouterr().out


def test_flake8_plugin_yields_findings():
    import ast

    from leakguard.flake8_plugin import LeakguardPlugin

    src = "import pandas as pd\ns = pd.Series([1])\nx = s.bfill()\n"
    out = list(LeakguardPlugin(ast.parse(src), src.splitlines(keepends=True)).run())
    assert out and out[0][2].startswith("LG004")


def test_unparseable_file_is_not_reported_clean(tmp_path, capsys):
    bad = write(tmp_path, "py2.py", "print 'hello'\n")
    assert main(["check", str(bad)]) == 2
    assert "SKIPPED" in capsys.readouterr().err


def test_bad_notebook_is_not_reported_clean(tmp_path, capsys):
    nb = write(tmp_path, "n.ipynb", "{not json")
    assert main(["check", str(nb)]) == 2


def test_hidden_ancestor_and_dotdot_do_not_hide_files(tmp_path, capsys):
    root = tmp_path / ".hidden" / "proj"
    root.mkdir(parents=True)
    write(root, "bad.py", "import pandas as pd\ns = pd.Series([1])\na = s.bfill()\n")
    assert main(["check", str(root)]) == 1


def test_empty_scan_is_an_error(tmp_path, capsys):
    assert main(["check", str(tmp_path)]) == 2


def test_unknown_select_rule_is_rejected(tmp_path):
    import pytest
    p = write(tmp_path, "m.py", "x = 1\n")
    with pytest.raises(SystemExit):
        main(["check", str(p), "--select", "LG0O1"])


def test_magics_inside_blocks_and_unparseable_cells(tmp_path, capsys):
    nb = {"cells": [
        {"cell_type": "code", "source": ["import pandas as pd\n", "s = pd.Series([1])\n", "if True:\n", "    %matplotlib inline\n", "x = s.bfill()"]},
        {"cell_type": "code", "source": ["%%bash\n", "echo hi && ((("]},
    ]}
    p = write(tmp_path, "n.ipynb", json.dumps(nb))
    assert main(["check", str(p)]) == 1  # the bfill is still found
    err = capsys.readouterr().err
    assert "not Python (%%bash)" in err and "[2]" in err


def nb_file(tmp_path, cells, name="n.ipynb", **meta):
    nb = {"nbformat": 4, "metadata": meta, "cells": [{"cell_type": "code", "source": c} for c in cells]}
    return write(tmp_path, name, json.dumps(nb))


LEAK = ["import pandas as pd\n", "s = pd.Series([1])\n"]


def test_code_behind_line_magics_is_checked(tmp_path, capsys):
    # `%time stmt` used to become `pass`, silently dropping the statement.
    for line in ["%time x = s.bfill()", "%timeit -n 10 -r 2 x = s.bfill()", "    %time x = s.bfill()"]:
        src = LEAK + (["if True:\n"] if line.startswith(" ") else []) + [line + "\n"]
        assert main(["check", str(nb_file(tmp_path, [src]))]) == 1, line
        assert "LG004" in capsys.readouterr().out


def test_ipython_syntax_does_not_blank_the_whole_cell(tmp_path, capsys):
    # One shell-assignment or help line used to make the whole cell unparseable, so it was skipped.
    for extra in ["files = !ls\n", "pd.Series?\n", "??pd.Series\n", "n = %who_ls\n", "!cli --a 1 \\\n      --b 2\n"]:
        p = nb_file(tmp_path, [LEAK[:1] + [extra] + LEAK[1:] + ["x = s.bfill()\n"]])
        assert main(["check", str(p)]) == 1, extra
        captured = capsys.readouterr()
        assert "LG004" in captured.out and "not checked" not in captured.err, extra


def test_python_cell_magics_are_checked_and_other_languages_are_named(tmp_path, capsys):
    p = nb_file(tmp_path, [["%%time\n"] + LEAK + ["x = s.bfill()\n"], ["%%bash\n", "echo hi && (((\n"]])
    assert main(["check", str(p)]) == 1  # a %%bash cell is not Python, so it doesn't make the scan incomplete
    captured = capsys.readouterr()
    assert "LG004" in captured.out and "%%bash" in captured.err


def test_unparseable_python_cell_makes_the_scan_incomplete(tmp_path, capsys):
    p = nb_file(tmp_path, [LEAK + ["x = s.bfill()\n"], ["def broken(:\n"]])
    assert main(["check", str(p)]) == 2  # findings are printed, but the exit code must not claim a full scan
    captured = capsys.readouterr()
    assert "LG004" in captured.out and "[2]" in captured.err


def test_nbformat3_notebooks_are_scanned(tmp_path, capsys):
    nb = {"nbformat": 3, "worksheets": [{"cells": [{"cell_type": "code", "input": LEAK + ["x = s.bfill()\n"]}]}]}
    assert main(["check", str(write(tmp_path, "old.ipynb", json.dumps(nb)))]) == 1
    assert "LG004" in capsys.readouterr().out


def test_non_python_and_unrecognised_notebooks_are_not_reported_clean(tmp_path, capsys):
    r = nb_file(tmp_path, [["library(dplyr)\n"]], name="r.ipynb", kernelspec={"language": "R", "name": "ir"})
    assert main(["check", str(r)]) == 2
    assert "not a Python notebook" in capsys.readouterr().err
    odd = write(tmp_path, "odd.ipynb", json.dumps({"nbformat": 4}))
    assert main(["check", str(odd)]) == 2


def test_missing_path_is_not_reported_clean(tmp_path, capsys):
    assert main(["check", str(tmp_path / "nope.py")]) == 2
    assert "SKIPPED" in capsys.readouterr().err


def test_clean_result_says_it_is_not_proof(tmp_path, capsys):
    assert main(["check", str(write(tmp_path, "ok.py", "x = 1\n"))]) == 0
    assert "not proof" in capsys.readouterr().err
