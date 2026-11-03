"""Parse a student's free-form answer into :class:`SubmittedIterations`.

The parser accepts the formats students actually produce when copying an AI
answer into the app:

* Markdown tables with a header such as
  ``| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |``.
* Labelled lines like ``Iterasi 1: conflict set R5, R1 -> R5 dipilih,
  kesimpulan Gangguan Provider``.
* Positional lines / ordered lists: ``1. R5 -> Gangguan Provider`` or
  ``Iterasi 5: STOP``.

The parser is intentionally lenient about whitespace, casing and bullet
characters, but it never guesses silently: text it cannot map to a field is
returned through :func:`parse_answer` as a list of unrecognized fragments so
the UI can warn about them.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .models import SubmittedIteration, SubmittedIterations

_STOP_CELLS = {"—", "–", "-", "--", "stop", "berhenti", "— (kosong)"}

_ARROW_SPLIT = re.compile(r"->|→|=>|⇒|;|\|")
_RULE_REF = re.compile(r"\b[Rr]\s*(\d+)\b")

# Ordered labels; the longest match wins when scanning a body.
_LABELS: List[Tuple[str, str]] = [
    ("conflict set", "conflict_set"),
    ("conflict", "conflict_set"),
    ("konflik", "conflict_set"),
    ("aturan terpilih", "selected"),
    ("aturan dipilih", "selected"),
    ("rule terpilih", "selected"),
    ("selected rule", "selected"),
    ("terpilih", "selected"),
    ("dipilih", "selected"),
    ("dijalankan", "selected"),
    ("kesimpulan", "conclusion"),
    ("conclusion", "conclusion"),
    ("hasil", "conclusion"),
]

_STOP_HINT = re.compile(r"\b(stop|berhenti|tidak ada aturan siap|conflict set kosong)\b",
                        re.IGNORECASE)


def _clean(text: str) -> str:
    return " ".join(str(text or "").strip().strip("*_`").split())


def _rule_refs(text: str) -> List[str]:
    """Return canonical rule ids (``R5``) in order of appearance."""
    return [f"R{m.group(1)}" for m in _RULE_REF.finditer(text or "")]


def _extract_labeled(body: str) -> dict:
    """Extract ``field -> value`` segments using the known keywords."""
    lowered = body.casefold()
    marks: List[Tuple[int, int, str]] = []
    for label, field in _LABELS:
        for match in re.finditer(re.escape(label), lowered):
            marks.append((match.start(), match.end(), field))
    marks.sort()

    # Drop overlapping marks (longer labels already cover shorter ones).
    filtered: List[Tuple[int, int, str]] = []
    last_end = -1
    for start, end, field in marks:
        if start >= last_end:
            filtered.append((start, end, field))
            last_end = end

    segments: dict = {"conflict_set": "", "selected": "", "conclusion": ""}
    for i, (start, end, field) in enumerate(filtered):
        next_start = filtered[i + 1][0] if i + 1 < len(filtered) else len(body)
        value = body[end:next_start]
        value = _ARROW_SPLIT.split(value)[0]  # stop at an arrow if one follows
        cleaned = _clean(value).strip(":：-–— ").strip()
        if field == "conflict_set" and cleaned.casefold().startswith("set"):
            cleaned = cleaned[3:].strip()  # "conflict set R5" -> keyword 'set'
        segments[field] = cleaned
    return segments


def _parse_conclusion_value(value: str) -> Optional[str]:
    value = _clean(value).strip(":：-–— ").strip()
    if not value or value.casefold() in _STOP_CELLS:
        return None
    return value


def _parse_body(body: str) -> Tuple[SubmittedIteration, List[str]]:
    """Parse the text after ``Iterasi N:`` into one iteration."""
    body = _clean(body)
    unrecognized: List[str] = []
    it = SubmittedIteration()

    if _STOP_HINT.search(body) and not _rule_refs(body):
        it.stop = True
        return it, unrecognized

    # Indonesian word order puts the value before the label:
    # "R5 dipilih" -> "dipilih R5" so the generic label scan works.
    body = re.sub(
        r"\b([Rr]\s*\d+)\s+(dipilih|terpilih|dijalankan)\b", r"\2 \1", body
    )

    segments = _extract_labeled(body)
    has_labels = any(segments.values())

    if has_labels:        # Conflict set value: rule refs only (facts are not part of the model).
        conflict_text = segments["conflict_set"]
        refs = _rule_refs(conflict_text)
        it.conflict_set = refs
        leftover = _RULE_REF.sub("", conflict_text)
        leftover = re.sub(r"[,\-/]+", " ", leftover).strip(" :：-–—")
        if leftover:
            unrecognized.append(leftover)

        selected_text = segments["selected"]
        sel_refs = _rule_refs(selected_text)
        if sel_refs:
            it.selected_rule = sel_refs[0]
        elif selected_text:
            it.selected_rule = _parse_conclusion_value(selected_text)

        it.conclusion = _parse_conclusion_value(segments["conclusion"])
        return it, unrecognized

    # Positional fallback: segment(s) split on arrows.
    parts = [p for p in ( _clean(x) for x in _ARROW_SPLIT.split(body) ) if p]
    if len(parts) >= 2:
        head, tail = parts[0], parts[-1]
        refs = _rule_refs(head)
        if refs:
            it.selected_rule = refs[0]
            for ref in refs[1:]:
                if ref not in it.conflict_set:
                    it.conflict_set.append(ref)
            leftover = _RULE_REF.sub("", head)
            leftover = re.sub(r"[,\-/]+", " ", leftover).strip(" :：-–—")
            if leftover:
                unrecognized.append(leftover)
        else:
            unrecognized.append(head)
        conclusion = _parse_conclusion_value(_RULE_REF.sub("", tail))
        if conclusion:
            it.conclusion = conclusion
        elif _rule_refs(tail):
            extra = _rule_refs(tail)
            for ref in extra:
                if ref not in it.conflict_set and ref != it.selected_rule:
                    it.conflict_set.append(ref)
        return it, unrecognized

    # Single segment: a bare list of rule ids or plain prose.
    refs = _rule_refs(body)
    if refs:
        it.selected_rule = refs[0]
        for ref in refs[1:]:
            if ref not in it.conflict_set:
                it.conflict_set.append(ref)
        return it, unrecognized

    # Plain prose without any rule reference is not an iteration claim.
    unrecognized.append(body)
    return it, unrecognized


# ---------------------------------------------------------------------------
# Markdown tables
# ---------------------------------------------------------------------------
def _looks_like_header(cells: List[str]) -> bool:
    keywords = ("iterasi", "iteration", "conflict", "konflik", "terpilih",
                "dipilih", "kesimpulan", "conclusion", "aturan", "rule")
    hits = sum(1 for cell in cells if any(k in cell.casefold() for k in keywords))
    return hits >= 2


def _header_fields(header_cells: List[str]) -> List[Optional[str]]:
    fields: List[Optional[str]] = []
    for cell in header_cells:
        key = cell.casefold()
        field_name: Optional[str] = None
        if "iterasi" in key or "iteration" in key:
            field_name = "iteration"
        elif "conflict" in key or "konflik" in key:
            field_name = "conflict_set"
        elif "terpilih" in key or "dipilih" in key or "selected" in key:
            field_name = "selected_rule"
        elif "kesimpulan" in key or "conclusion" in key or "hasil" in key:
            field_name = "conclusion"
        fields.append(field_name)
    return fields


def _parse_table(lines: List[str], start: int) -> Tuple[SubmittedIterations, int]:
    """Parse a markdown table whose header is at ``lines[start]``."""
    header_cells = [_clean(c) for c in lines[start].strip().strip("|").split("|")]
    col_fields = _header_fields(header_cells)

    iterations = SubmittedIterations()
    i = start + 1
    if i < len(lines) and re.fullmatch(r"[\s|:\-–—]+", lines[i] or ""):
        i += 1  # separator row

    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        cells = [_clean(c) for c in line.strip("|").split("|")]
        it = SubmittedIteration(source_line=i + 1)
        for idx, cell in enumerate(cells):
            if not cell or cell.casefold() in _STOP_CELLS:
                continue
            field_name = col_fields[idx] if idx < len(col_fields) else None
            if field_name == "iteration":
                if re.fullmatch(r"\d+", cell):
                    it.iteration = int(cell)
            elif field_name == "conflict_set":
                for ref in _rule_refs(cell):
                    if ref not in it.conflict_set:
                        it.conflict_set.append(ref)
            elif field_name == "selected_rule":
                refs = _rule_refs(cell)
                it.selected_rule = refs[0] if refs else cell
            elif field_name == "conclusion":
                it.conclusion = _parse_conclusion_value(cell)
            else:
                # Unknown column: best effort.
                refs = _rule_refs(cell)
                if refs and not it.selected_rule:
                    it.selected_rule = refs[0]
                    for ref in refs[1:]:
                        if ref not in it.conflict_set:
                            it.conflict_set.append(ref)
                elif it.conclusion is None:
                    it.conclusion = _parse_conclusion_value(cell)
        if _STOP_HINT.search(" ".join(cells)) and not (
            it.conflict_set or it.selected_rule
        ):
            it.stop = True
        iterations.iterations.append(it)
        i += 1

    return iterations, i


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
_ITER_PREFIX = re.compile(
    r"^\s*[-*•]?\s*(?:iterasi|iteration|langkah)\s*(\d+)\s*[:\-–—]\s*(.*)$",
    re.IGNORECASE,
)
_ORDERED_PREFIX = re.compile(r"^\s*[-*•]?\s*(\d+)[\.\)]\s+(.*)$")


def parse_answer(text: str) -> Tuple[SubmittedIterations, List[str]]:
    """Parse pasted text.

    Returns the parsed iterations plus unrecognized fragments (prefixed with
    their line number) so the UI can warn about parts it could not read.
    """
    lines = (text or "").replace("\r\n", "\n").split("\n")
    iterations = SubmittedIterations()
    unrecognized: List[str] = []

    table_start: Optional[int] = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and _looks_like_header(
            [_clean(c) for c in stripped.strip("|").split("|")]
        ):
            table_start = idx
            break

    consumed_until = 0
    if table_start is not None:
        parsed, consumed_until = _parse_table(lines, table_start)
        iterations.iterations.extend(parsed.iterations)

    for idx in range(consumed_until, len(lines)):
        line = lines[idx].strip()
        if not line:
            continue

        iter_match = _ITER_PREFIX.match(line)
        ordered_match = _ORDERED_PREFIX.match(line)
        body: Optional[str] = None
        number: Optional[int] = None

        if iter_match:
            number = int(iter_match.group(1))
            body = iter_match.group(2)
        elif ordered_match:
            number = int(ordered_match.group(1))
            body = ordered_match.group(2)
        else:
            body = line

        it, leftover = _parse_body(body)
        it.source_line = idx + 1
        if number is not None:
            it.iteration = number
        if leftover:
            unrecognized.extend(f"baris {idx + 1}: {frag}" for frag in leftover)

        if it.stop or it.conflict_set or it.selected_rule or it.conclusion:
            iterations.iterations.append(it)
        elif iter_match:
            # "Iterasi 5:" with an unreadable body — still record the claim so
            # the checker can report the missing content.
            it.stop = False
            iterations.iterations.append(it)
        else:
            unrecognized.append(f"baris {idx + 1}: {line[:60]}")

    # Number unlabeled iterations sequentially.
    next_num = 1
    for it in iterations.iterations:
        if not it.iteration:
            it.iteration = next_num
        next_num = max(next_num, it.iteration) + 1

    return iterations, unrecognized
