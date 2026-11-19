"""Tiny YAML-subset reader so the tools need no pip packages.

Supports exactly what feeds.yml and watch-keywords.yml use:
  - '#' comments (outside quotes), blank lines
  - nested block mappings (indent = 2+ spaces, consistent per level)
  - block lists:  '- scalar'  and  '- key: value' (+ continuation keys, indented)
  - inline lists: [a, b, "c d"]
  - scalars: "quoted", 'quoted', true/false/yes/no, null/~, ints, floats, bare strings
If PyYAML is installed it is used instead (same results for these files).
"""
from __future__ import annotations
import re

try:  # pragma: no cover
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None


def _strip_comment(s: str) -> str:
    out, q = [], None
    for i, ch in enumerate(s):
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'" and (i == 0 or s[i - 1] in " \t[,:-"):
            q = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _split_inline(s: str):
    parts, cur, q, depth = [], [], None, 0
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur.append(ch)
        elif ch == "[":
            depth += 1
            cur.append(ch)
        elif ch == "]":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


def _scalar(s: str):
    s = s.strip()
    if s == "":
        return None
    if s[0] in "\"'" and s[-1] == s[0] and len(s) >= 2:
        return s[1:-1].replace("\\\"", "\"") if s[0] == '"' else s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(p) for p in _split_inline(s[1:-1])]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _kv(s: str):
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*:(?:\s+(.*))?$", s)
    if not m:
        return None
    return m.group(1), (m.group(2) if m.group(2) is not None else "")


def _parse_block(lines, i, indent):
    """lines: list of (indent, text). Returns (value, next_i)."""
    if i >= len(lines):
        return None, i
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        out = []
        while i < len(lines) and lines[i][0] == indent and (lines[i][1].startswith("- ") or lines[i][1] == "-"):
            body = lines[i][1][2:].strip() if lines[i][1] != "-" else ""
            kv = _kv(body) if body else None
            if kv and not body.startswith(("\"", "'", "[")):
                # list of mappings: first key inline, continuation keys deeper
                item = {}
                key, val = kv
                sub_indent = indent + 2
                i += 1
                if val.strip() == "":
                    if i < len(lines) and lines[i][0] > indent + 1:
                        item[key], i = _parse_block(lines, i, lines[i][0])
                    else:
                        item[key] = None
                else:
                    item[key] = _scalar(val)
                while i < len(lines) and lines[i][0] > indent:
                    ind2 = lines[i][0]
                    kv2 = _kv(lines[i][1])
                    if not kv2:
                        raise ValueError(f"bad line in list item: {lines[i][1]!r}")
                    k2, v2 = kv2
                    i += 1
                    if v2.strip() == "":
                        if i < len(lines) and lines[i][0] > ind2:
                            item[k2], i = _parse_block(lines, i, lines[i][0])
                        else:
                            item[k2] = None
                    else:
                        item[k2] = _scalar(v2)
                out.append(item)
            else:
                out.append(_scalar(body))
                i += 1
        return out, i
    out = {}
    while i < len(lines) and lines[i][0] == indent:
        kv = _kv(lines[i][1])
        if not kv:
            raise ValueError(f"bad line: {lines[i][1]!r}")
        key, val = kv
        i += 1
        if val.strip() == "":
            if i < len(lines) and lines[i][0] > indent:
                out[key], i = _parse_block(lines, i, lines[i][0])
            elif i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                out[key], i = _parse_block(lines, i, indent)
            else:
                out[key] = None
        else:
            out[key] = _scalar(val)
    return out, i


def loads(text: str):
    if _yaml is not None:
        return _yaml.safe_load(text)
    lines = []
    for raw in text.splitlines():
        s = _strip_comment(raw.replace("\t", "  "))
        if not s.strip():
            continue
        lines.append((len(s) - len(s.lstrip(" ")), s.strip()))
    if not lines:
        return {}
    val, _ = _parse_block(lines, 0, lines[0][0])
    return val


def load(path: str):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())
