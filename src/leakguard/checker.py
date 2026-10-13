from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass

from .rules import RULES

TRANSFORMERS = {
    "StandardScaler", "MinMaxScaler", "RobustScaler", "MaxAbsScaler", "PowerTransformer",
    "QuantileTransformer", "OneHotEncoder", "OrdinalEncoder", "LabelEncoder", "TargetEncoder", "SimpleImputer",
    "KNNImputer", "IterativeImputer", "PCA", "TruncatedSVD", "SelectKBest", "SelectPercentile", "VarianceThreshold",
    "TfidfVectorizer", "CountVectorizer", "KBinsDiscretizer",
}
TARGET_COL = re.compile(r"^(y|target|label|y_true)$", re.I)
TARGETISH = re.compile(r"(target|label|^y$|_y$|^y_|fwd|forward|future|next|ahead|outcome)", re.I)
TIME_NAMES = re.compile(r"(?<![a-z])(date|datetime|time|timestamp|dt|year|month|day|period)(?![a-z])", re.I)
TIME_CALLS = {"to_datetime", "resample", "rolling", "shift", "ewm", "pct_change", "DatetimeIndex", "date_range", "asfreq"}
IGNORE = re.compile(r"#\s*leakguard:\s*ignore(?:\[([A-Z0-9,\s]+)\])?", re.I)


@dataclass(frozen=True, order=True)
class Finding:
    line: int
    col: int
    rule: str
    message: str

    def format(self, path: str) -> str:
        return f"{path}:{self.line}:{self.col + 1}: {self.rule} {self.message}"


def _call_name(node: ast.Call) -> str | None:
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _const(node: ast.AST | None):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        v = node.operand.value
        return -v if isinstance(v, (int, float)) else None
    return None


def _kw(node: ast.Call, name: str) -> ast.AST | None:
    return next((k.value for k in node.keywords if k.arg == name), None)


def _suppressions(source: str) -> dict[int, set[str] | None]:
    """line -> set of suppressed rule IDs (None = all)."""
    out: dict[int, set[str] | None] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT and (m := IGNORE.search(tok.string)):
                out[tok.start[0]] = {s.strip().upper() for s in m.group(1).split(",")} if m.group(1) else None
    except (tokenize.TokenError, IndentationError):
        pass
    return out


def _scope_nodes(scope: ast.AST):
    """Nodes in this scope, not descending into nested function or class definitions."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        n = stack.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(n))


def _used_names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _target_roots(target: ast.AST) -> set[str]:
    """Root variable names written by an assignment target (x, x[...], x.attr, (a, b))."""
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return set().union(*(_target_roots(e) for e in target.elts)) if target.elts else set()
    if isinstance(target, (ast.Subscript, ast.Attribute)):
        return _target_roots(target.value)
    return set()


def _lineage(nodes: list[ast.AST], seeds: set[str], before_line: int) -> dict[str, set[int]]:
    """Names that `seeds` were computed from, through assignments before `before_line`.

    Maps each name to the lines at which its value was read, so a caller can tell whether a name was rebound in
    between (notebooks reuse `X` for unrelated datasets). Ignores control flow: the latest assignment above wins.
    """
    defs: dict[str, list[tuple[int, set[str], bool]]] = {}
    for n in nodes:
        if isinstance(n, ast.Assign) and n.lineno < before_line:
            used = _used_names(n.value)
            for t in n.targets:
                for r in _target_roots(t):
                    # plain re-assignment replaces the value; df["c"] = ... adds to df, doesn't replace it
                    defs.setdefault(r, []).append((n.lineno, used, isinstance(t, ast.Name)))
    reads: dict[str, set[int]] = {}
    stack = [(s, before_line) for s in seeds]
    while stack:
        name, line = stack.pop()
        if line in reads.setdefault(name, set()):
            continue
        reads[name].add(line)
        for def_line, used, plain in reversed(defs.get(name, [])):
            if def_line >= line:
                continue
            stack.extend((u, def_line) for u in used)
            if plain:
                break
    return reads


def _same_binding_read(nodes: list[ast.AST], name: str, at: int, reads: set[int]) -> bool:
    """Whether `name` as bound at line `at` is the value read at one of `reads` (no plain rebinding in between)."""
    rebinds = [n.lineno for n in nodes if isinstance(n, ast.Assign) and at < n.lineno
               and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    return any(line > at and not any(r < line for r in rebinds) for line in reads)


def _first_split_fed(nodes: list[ast.AST], feeds: list[tuple[ast.Call, dict[str, set[int]]]], node: ast.AST,
                     touched: set[str]) -> ast.Call | None:
    """The earliest split after `node` whose arrays were computed from any of `touched`, as bound at `node`."""
    return next((sc for sc, lineage in feeds if sc.lineno > node.lineno
                 and any(t in lineage and _same_binding_read(nodes, t, node.lineno, lineage[t]) for t in touched)), None)


def _receiver_root(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
        node = node.value if not isinstance(node, ast.Call) else node.func
    return node.id if isinstance(node, ast.Name) else None


def _is_timey(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and _call_name(n) in TIME_CALLS:
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and TIME_NAMES.search(n.value) and len(n.value) < 30:
            return True
        if isinstance(n, ast.Name) and TIME_NAMES.search(n.id):
            return True
    return False


def _has_time_signal(tree: ast.AST) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n) in TIME_CALLS:
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and TIME_NAMES.search(n.value) and len(n.value) < 30:
            return True
        if isinstance(n, ast.Name) and TIME_NAMES.search(n.id):
            return True
    return False


def _assigned_names(tree: ast.AST) -> dict[int, list[str]]:
    """Map id(value node) -> names/column keys it is assigned to."""
    out: dict[int, list[str]] = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            names: list[str] = []
            for t in targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
                elif isinstance(t, ast.Subscript):
                    c = _const(t.slice)
                    if isinstance(c, str):
                        names.append(c)
                    if isinstance(t.value, ast.Name):
                        names.append(t.value.id)
                elif isinstance(t, ast.Attribute):
                    names.append(t.attr)
            if n.value is not None:
                for sub in ast.walk(n.value):
                    out.setdefault(id(sub), []).extend(names)
    return out


def check_source(source: str, filename: str = "<string>") -> list[Finding]:
    tree = ast.parse(source, filename)  # SyntaxError propagates: an unparseable file must not look clean
    findings: list[Finding] = []
    add = lambda node, rule, **fmt: findings.append(  # noqa: E731
        Finding(node.lineno, node.col_offset, rule, RULES[rule][1].format(**fmt)))
    assigned = _assigned_names(tree)
    timey = _has_time_signal(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)

        if name == "shift":
            arg = node.args[0] if node.args else _kw(node, "periods")
            n = _const(arg)
            if isinstance(n, (int, float)) and n < 0 and not any(TARGETISH.search(x) for x in assigned.get(id(node), [])):
                add(node, "LG001", n=int(n))

        elif name == "rolling" and _const(_kw(node, "center")) is True:
            add(node, "LG002")

        elif name in {"rolling", "expanding", "ewm"} and not _const(_kw(node, "center")):
            src = node.func.value if isinstance(node.func, ast.Attribute) else None
            col = None
            if isinstance(src, ast.Subscript):
                col = _const(src.slice) if isinstance(_const(src.slice), str) else None
            elif isinstance(src, ast.Name):
                col = src.id
            # climb to the enclosing statement's chain to see whether a shift happens before the aggregation
            chain_has_shift = any(isinstance(n, ast.Call) and _call_name(n) == "shift" for n in ast.walk(src)) if src is not None else False
            assigned_feature = any(not TARGETISH.search(x) for x in assigned.get(id(node), []))
            if col and TARGET_COL.search(col) and not chain_has_shift and assigned_feature:
                add(node, "LG008", call=f".{name}()", col=col)

        elif name in {"bfill", "backfill"}:
            add(node, "LG004", call=f".{name}()")
        elif name == "fillna" and _const(_kw(node, "method")) in {"bfill", "backfill"}:
            add(node, "LG004", call=f".fillna(method={_const(_kw(node, 'method'))!r})")
        elif name == "interpolate":
            # Linear (and most) interpolation uses the NEXT known value whatever limit_direction says.
            if _const(_kw(node, "method")) not in {"pad", "ffill"}:
                add(node, "LG004", call=".interpolate()")

        elif name == "merge_asof" and _const(_kw(node, "direction")) in {"forward", "nearest"}:
            add(node, "LG005", direction=_const(_kw(node, "direction")))

        elif name in {"KFold", "ShuffleSplit"} and timey:
            if name != "KFold" or _const(_kw(node, "shuffle")) is True:
                add(node, "LG006", what=f"`{name}`")

    # Scope-ordered checks: LG003 and LG007 need "earlier than a split, and feeds that split". A notebook often
    # holds several unrelated splits in one scope, so every split is checked, not only the first.
    modules = {(a.asname or a.name).split(".")[0] for n in ast.walk(tree)
               if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    scopes: list[ast.AST] = [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for scope in scopes:
        nodes = sorted((n for n in _scope_nodes(scope) if hasattr(n, "lineno")), key=lambda n: (n.lineno, n.col_offset))
        split_calls = [n for n in nodes if isinstance(n, ast.Call) and _call_name(n) == "train_test_split"]
        if not split_calls:
            continue
        # What each split's arrays were computed from. Imported module names (np, pd) are not data lineage.
        feeds: list[tuple[ast.Call, dict[str, set[int]]]] = []
        for sc in split_calls:
            args = set().union(*(_used_names(a) for a in sc.args)) if sc.args else set()
            feeds.append((sc, {k: v for k, v in _lineage(nodes, args - modules, sc.lineno).items() if k not in modules}))

        # LG006: a random split matters only if the data being split is time-ordered. Evidence: a time-ish call
        # or column name in how those arrays were built (not merely somewhere else in the file).
        for sc, lineage in feeds:
            if _const(_kw(sc, "shuffle")) is False or _kw(sc, "stratify") is not None:
                continue
            timey_names: set[str] = set()
            for n in nodes:
                if isinstance(n, ast.Assign) and n.lineno < sc.lineno and _is_timey(n.value):
                    timey_names |= set().union(*(_target_roots(t) for t in n.targets))
            if (lineage.keys() & timey_names) or any(_is_timey(a) for a in sc.args):
                add(sc, "LG006", what="`train_test_split` (shuffle defaults to True)")

        stmt_out: dict[int, set[str]] = {}
        for n in nodes:
            if isinstance(n, ast.Assign):
                roots = set().union(*(_target_roots(t) for t in n.targets))
                for sub in ast.walk(n.value):
                    stmt_out[id(sub)] = roots

        last_split = split_calls[-1].lineno
        is_transformer: dict[str, bool] = {}  # flow-sensitive: the latest assignment decides
        for n in nodes:
            if isinstance(n, ast.Assign):
                ctor = isinstance(n.value, ast.Call) and _call_name(n.value) in TRANSFORMERS
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        is_transformer[t.id] = ctor
            if not isinstance(n, ast.Call) or n.lineno >= last_split or not isinstance(n.func, ast.Attribute):
                continue
            touched = _used_names(ast.Module(body=[ast.Expr(a) for a in n.args], type_ignores=[])) | stmt_out.get(id(n), set())
            if n.func.attr in {"fit", "fit_transform"}:
                owner, label = n.func.value, None
                if isinstance(owner, ast.Name) and is_transformer.get(owner.id):
                    label = f"{owner.id}.{n.func.attr}"
                elif isinstance(owner, ast.Call) and _call_name(owner) in TRANSFORMERS:
                    label = f"{_call_name(owner)}().{n.func.attr}"
                if label and (sc := _first_split_fed(nodes, feeds, n, touched)):
                    add(n, "LG003", call=label, split=sc.lineno)
            elif n.func.attr == "fillna" and n.args:
                a0 = n.args[0]
                if isinstance(a0, ast.Call) and isinstance(a0.func, ast.Attribute) and a0.func.attr in {"mean", "median", "mode"}:
                    recv = _receiver_root(n.func.value)
                    if sc := _first_split_fed(nodes, feeds, n, ({recv} if recv else set()) | stmt_out.get(id(n), set())):
                        add(n, "LG007", stat=f".{a0.func.attr}()", split=sc.lineno)

    sup = _suppressions(source)
    kept = []
    for f in sorted(set(findings)):
        s = sup.get(f.line, False)
        if s is False or (s is not None and f.rule not in s):
            kept.append(f)
    return kept
