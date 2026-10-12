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
    assert "not plain Python" in err and "[2]" in err
