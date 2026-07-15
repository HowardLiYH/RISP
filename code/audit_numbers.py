#!/usr/bin/env python3
"""audit_numbers.py -- automated number audit for paper/main.tex.

Guards against numbers-drift bugs: every quoted number in the paper that
traces to a released result JSON is re-extracted from the tex with a regex,
recomputed from the JSON source, and compared. Any mismatch is a FAIL and
the script exits nonzero.

Usage
-----
    python3 code/audit_numbers.py                    # run the full audit
    python3 code/audit_numbers.py --filter tab1      # only claims whose id contains "tab1"
    python3 code/audit_numbers.py --verbose          # show sources/patterns for failures
    python3 code/audit_numbers.py --manifest code/audit_manifest.json --tex "paper/main.tex"

Run from anywhere; paths in the manifest are relative to the repo root
(the parent of code/).

Manifest format (code/audit_manifest.json)
------------------------------------------
    {
      "tex_file": "paper/main.tex",
      "claims": [ <claim>, ... ]
    }

Each <claim> is one checked number:

    {
      "id":          "e1.tab1.A6.post.mean",       # unique name, used in output
      "tex_pattern": "regex with capture group(s)",# matched against the WHITESPACE-
                                                   # NORMALIZED, comment-stripped tex
                                                   # (all runs of whitespace -> one space),
      "group":       1,                            # which capture group holds the number
                                                   # (default 1)
      "expect":      <source>,                     # how to recompute the true value
      "tolerance":   "auto" | <float>,             # default "auto": half a unit in the
                                                   # last quoted decimal place
      "cmp":         "eq" | "le" | "ge",           # default "eq".
                                                   #   eq: |expected - quoted| <= tol
                                                   #   le: expected <= quoted + tol
                                                   #       (for "all <= X" claims)
                                                   #   ge: expected >= quoted - tol
                                                   #       (for "all > X" claims)
      "abs":         false,                        # compare |values| (when the sign is
                                                   # carried by surrounding prose)
      "note":        "free text"                   # shown on failure
    }

<source> is either a direct JSON reference:

    {"path": "results_100seed/e1_synth.json:post_react/A6-risp-inv/mean"}

(file, then ':', then a '/'-separated key path -- '/' not '.' because some
JSON keys contain dots, e.g. the SNR key "0.5"; list indices are integers)

or a transform with named inputs:

    {"expr": "(a-b)/a*100",
     "inputs": {"a": "results_100seed/e1_synth.json:post_react/A2-router/mean",
                "b": "results_100seed/e1_synth.json:post_react/A5-risp-erm/mean"}}

The expr mini-language is a Python expression over the named inputs with the
following whitelisted helpers (no other builtins):

    abs, min, max, round, len, sqrt, exp, log, erfc,
    mean(xs), stdev(xs),               # over a list-valued input
    ci95(xs)  = 1.96*stdev(xs)/sqrt(n) # normal 95% half-width over a list
    vadd(a,b), vsub(a,b)               # elementwise on two equal-length lists
    normal_p_one_sided(z) = erfc(z/sqrt(2))/2

Inputs may resolve to floats or lists (lists are for mean/stdev/ci95/v* use).

Adding a claim = adding one manifest entry. Number parsing on the tex side
understands plain decimals ("0.0308", "-4.3"), LaTeX scientific notation
("2.5\\times10^{-7}", "6.0{\\times}10^{-23}"), and brace-comma thousands
separators ("2{,}953").

Auto tolerance: a quote with d decimals in its mantissa passes iff the
recomputed value is within half a unit of the last quoted digit
(0.5 * 10^-d, scaled by the exponent for scientific notation) -- i.e. the
quote is a correct rounding of the recomputed value. Claims quoted with
"~"/"approx" in the paper carry an explicit looser "tolerance" in the
manifest.

Exit status: 0 iff every claim PASSes (and every pattern matched exactly
once); 1 otherwise.
"""

import argparse
import json
import math
import os
import re
import statistics
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = os.path.join(REPO_ROOT, "code", "audit_manifest.json")

# --------------------------------------------------------------------------
# tex handling
# --------------------------------------------------------------------------

def load_normalized_tex(path):
    """Read tex, strip (unescaped) % comments, collapse all whitespace runs
    to single spaces.  All manifest patterns are written against this
    normalized single-line form, so claims may span source line breaks."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    # strip comments: an unescaped % up to end of line
    stripped = re.sub(r"(?<!\\)%[^\n]*", "", raw)
    return re.sub(r"\s+", " ", stripped)


_NUM_RE = re.compile(
    r"^\s*([+-]?\d*\.?\d+)\s*(?:\\times\s*10\^\{?([+-]?\d+)\}?)?\s*$"
)


def parse_tex_number(s):
    """Parse a captured tex number string.

    Returns (value, auto_tolerance).  Handles '0.0308', '-4.3',
    '2.5\\times10^{-7}', '6.0{\\times}10^{-23}', '2{,}953', '1{,}500'.
    Auto tolerance is half a unit in the last quoted decimal place
    (x 10^exponent for scientific notation), i.e. the quote passes iff it is
    a correct rounding of the recomputed value.
    """
    t = s.strip()
    t = t.replace("{,}", "").replace(",", "")
    t = t.replace("{\\times}", "\\times")
    t = t.replace("−", "-")  # unicode minus, just in case
    m = _NUM_RE.match(t)
    if not m:
        raise ValueError("cannot parse tex number: %r" % s)
    mant, expo = m.group(1), m.group(2)
    exp = int(expo) if expo else 0
    value = float(mant) * (10.0 ** exp)
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    tol = 0.5 * (10.0 ** -decimals) * (10.0 ** exp)
    # tiny slack for float representation of the recomputed value
    tol *= 1.0 + 1e-9
    tol += 1e-15
    return value, tol


# --------------------------------------------------------------------------
# JSON reference resolution
# --------------------------------------------------------------------------

_JSON_CACHE = {}


def _load_json(relpath):
    if relpath not in _JSON_CACHE:
        with open(os.path.join(REPO_ROOT, relpath), "r", encoding="utf-8") as fh:
            _JSON_CACHE[relpath] = json.load(fh)
    return _JSON_CACHE[relpath]


def resolve_ref(ref):
    """Resolve 'file.json:key/key/key' -> value (float, int, or list).

    Path separator is '/' (some JSON keys contain '.').  A path component
    indexes a dict by string key, or a list by integer.
    """
    try:
        fpart, kpart = ref.split(":", 1)
    except ValueError:
        raise ValueError("bad json ref (missing ':'): %r" % ref)
    node = _load_json(fpart)
    if kpart:
        for comp in kpart.split("/"):
            # JSON keys that themselves contain '/' (e.g. "4H/L2b") are
            # written in the manifest with U+2215 DIVISION SLASH instead:
            comp = comp.replace("∕", "/")
            if isinstance(node, dict):
                if comp not in node:
                    raise KeyError("key %r not found in %s (have: %s)"
                                   % (comp, fpart, list(node)[:12]))
                node = node[comp]
            elif isinstance(node, list):
                node = node[int(comp)]
            else:
                raise KeyError("cannot descend into %r at %r" % (type(node), comp))
    return node


# --------------------------------------------------------------------------
# expr mini-language
# --------------------------------------------------------------------------

def _ci95(xs):
    return 1.96 * statistics.stdev(xs) / math.sqrt(len(xs))


def _vadd(a, b):
    return [x + y for x, y in zip(a, b)]


def _vsub(a, b):
    return [x - y for x, y in zip(a, b)]


_EXPR_ENV = {
    "abs": abs, "min": min, "max": max, "round": round, "len": len,
    "sqrt": math.sqrt, "exp": math.exp, "log": math.log, "erfc": math.erfc,
    "mean": statistics.mean, "stdev": statistics.stdev, "ci95": _ci95,
    "vadd": _vadd, "vsub": _vsub,
    "normal_p_one_sided": lambda z: math.erfc(z / math.sqrt(2)) / 2.0,
}


def compute_expected(expect):
    """Evaluate an 'expect' source: {'path': ref} or {'expr':…, 'inputs':…}."""
    if "path" in expect:
        val = resolve_ref(expect["path"])
        if not isinstance(val, (int, float)):
            raise ValueError("ref %r resolved to non-scalar %r"
                             % (expect["path"], type(val)))
        return float(val)
    if "expr" in expect:
        env = dict(_EXPR_ENV)
        for name, ref in expect.get("inputs", {}).items():
            env[name] = resolve_ref(ref)
        return float(eval(expect["expr"], {"__builtins__": {}}, env))  # noqa: S307
    raise ValueError("expect needs 'path' or 'expr': %r" % expect)


# --------------------------------------------------------------------------
# claim checking
# --------------------------------------------------------------------------

class Result(object):
    __slots__ = ("id", "status", "quoted", "expected", "tol", "detail", "claim")

    def __init__(self, cid, status, quoted=None, expected=None, tol=None,
                 detail="", claim=None):
        self.id, self.status = cid, status
        self.quoted, self.expected, self.tol = quoted, expected, tol
        self.detail, self.claim = detail, claim


def check_claim(claim, tex):
    cid = claim["id"]
    try:
        matches = list(re.finditer(claim["tex_pattern"], tex))
        if len(matches) == 0:
            return Result(cid, "FAIL", detail="tex pattern not found", claim=claim)
        if len(matches) > 1 and not claim.get("allow_multiple", False):
            return Result(cid, "FAIL",
                          detail="tex pattern matched %d times (want 1)" % len(matches),
                          claim=claim)
        captured = matches[0].group(claim.get("group", 1))
        quoted, auto_tol = parse_tex_number(captured)
        expected = compute_expected(claim["expect"])
        if claim.get("abs", False):
            quoted, expected = abs(quoted), abs(expected)
        tol = claim.get("tolerance", "auto")
        tol = auto_tol if tol == "auto" else float(tol)
        cmp_mode = claim.get("cmp", "eq")
        if cmp_mode == "eq":
            ok = abs(expected - quoted) <= tol
        elif cmp_mode == "le":
            ok = expected <= quoted + tol
        elif cmp_mode == "ge":
            ok = expected >= quoted - tol
        else:
            raise ValueError("bad cmp: %r" % cmp_mode)
        return Result(cid, "PASS" if ok else "FAIL",
                      quoted=quoted, expected=expected, tol=tol,
                      detail="" if ok else "cmp=%s" % cmp_mode, claim=claim)
    except Exception as exc:  # manifest/data errors are audit failures too
        return Result(cid, "ERROR", detail="%s: %s" % (type(exc).__name__, exc),
                      claim=claim)


def fmt(x):
    if x is None:
        return "-"
    if x == 0:
        return "0"
    if abs(x) >= 1e-3 and abs(x) < 1e6:
        return ("%.6f" % x).rstrip("0").rstrip(".")
    return "%.4g" % x


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit paper numbers against result JSONs.")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--tex", default=None,
                    help="override the manifest's tex_file (path relative to repo root or absolute)")
    ap.add_argument("--filter", default=None,
                    help="only run claims whose id contains this substring")
    ap.add_argument("--verbose", action="store_true",
                    help="print pattern/source detail for failures")
    args = ap.parse_args(argv)

    with open(args.manifest, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    tex_path = args.tex or manifest["tex_file"]
    if not os.path.isabs(tex_path):
        tex_path = os.path.join(REPO_ROOT, tex_path)
    tex = load_normalized_tex(tex_path)

    claims = manifest["claims"]
    if args.filter:
        claims = [c for c in claims if args.filter in c["id"]]

    ids = [c["id"] for c in claims]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        print("MANIFEST ERROR: duplicate claim ids: %s" % sorted(dupes))
        return 1

    results = [check_claim(c, tex) for c in claims]

    wid = max([len(r.id) for r in results] + [4])
    print("%-6s %-*s %14s %14s %10s" % ("STATUS", wid, "claim", "quoted", "recomputed", "tol"))
    print("-" * (6 + 1 + wid + 3 * 15 + 11))
    for r in results:
        print("%-6s %-*s %14s %14s %10s%s" % (
            r.status, wid, r.id, fmt(r.quoted), fmt(r.expected), fmt(r.tol),
            ("  " + r.detail) if (r.detail and r.status != "PASS") else ""))

    bad = [r for r in results if r.status != "PASS"]
    if bad:
        print("\n" + "=" * 72)
        print("FAILURES (%d):" % len(bad))
        for r in bad:
            print("\n  [%s] %s" % (r.status, r.id))
            print("    quoted=%s  recomputed=%s  tol=%s  %s"
                  % (fmt(r.quoted), fmt(r.expected), fmt(r.tol), r.detail))
            if r.claim is not None:
                if r.claim.get("note"):
                    print("    note: %s" % r.claim["note"])
                if args.verbose:
                    print("    pattern: %s" % r.claim["tex_pattern"])
                    print("    expect:  %s" % json.dumps(r.claim["expect"]))

    npass = sum(1 for r in results if r.status == "PASS")
    print("\nSUMMARY: %d claims checked | %d PASS | %d FAIL | %d ERROR"
          % (len(results), npass,
             sum(1 for r in results if r.status == "FAIL"),
             sum(1 for r in results if r.status == "ERROR")))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
