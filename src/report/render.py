"""Render a professional, print-ready (black & white) report from a trace.

The renderer is deliberately UI-independent: it consumes plain trace models
and returns an HTML document (``str``) or a Markdown document (``str``).  The
Streamlit page only wires user input to :func:`render_html` /
:func:`render_markdown`.

The layout follows a conventional academic/technical report: a cover page with
an optional identity block, numbered sections, monospaced-free serif body text,
black rules and grey table headers — no colour accents, so it prints cleanly.
"""

from __future__ import annotations

import html
from typing import Dict, List, Optional, Sequence

from ..models import BackwardNode, BackwardResult, ForwardResult, Rule, salience_label

# Monochrome palette (kept local so the report never inherits the app theme).
_INK = "#111111"
_MUTED = "#4b5563"
_SOFT = "#f0f0f0"

_DEFAULT_BACKGROUND = (
    "Gangguan koneksi internet dapat disebabkan oleh berbagai sumber, mulai dari "
    "perangkat pengguna, router, hingga penyedia layanan. NetExpert memodelkan "
    "penalaran diagnosis tersebut sebagai sistem pakar berbasis aturan produksi "
    "IF–THEN. Setiap aturan diuji terhadap sekumpulan fakta awal pada working "
    "memory, dan keputusan yang diambil dicatat secara eksplisit sehingga seluruh "
    "proses dapat diaudit."
)


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _md_cell(value) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


# ---------------------------------------------------------------------------
# Content assembly (shared by both renderers)
# ---------------------------------------------------------------------------
def build_cover(meta) -> Dict[str, object]:
    """Turn a :class:`ReportMeta` into a renderable cover description."""
    identity: List[List[str]] = []

    def add(label: str, value: str) -> None:
        value = str(value or "").strip()
        if value:
            identity.append([label, value])

    add("Mata Kuliah", meta.course)
    add("Kelompok", meta.group_label)
    add("Dosen Pengampu", meta.lecturer)
    add("Asisten / Pembimbing", meta.assistant)
    add("Program Studi", meta.program_study)
    add("Jurusan / Departemen", meta.department)
    add("Fakultas", meta.faculty)
    add("Kota", meta.city)
    add("Tanggal", meta.date)

    return {
        "title": str(meta.title).strip() or "Laporan",
        "subtitle": str(meta.assignment).strip(),
        "logo": str(meta.logo_data_url or ""),
        "identity": identity,
        "members": [member.one_line() for member in meta.real_members],
        "institution": str(meta.institution).strip(),
        "group_label": meta.group_label,
    }


def _auto_summary(forward, backward, rules) -> str:
    parts: List[str] = []
    if rules:
        parts.append(f"penalaran menggunakan {len(rules)} aturan produksi IF–THEN")
    if forward:
        parts.append(
            f"forward chaining menembakkan {len(forward.fired_rules)} aturan "
            f"hingga working memory akhir memuat {len(forward.final_facts)} fakta"
        )
    if backward:
        verdict = "berhasil membuktikan" if backward.proven else "tidak dapat membuktikan"
        parts.append(f"backward chaining {verdict} goal '{backward.goal}'")
    if not parts:
        return (
            "Belum ada hasil inferensi pada sesi ini. Jalankan forward chaining "
            "atau backward chaining pada halaman Diagnosis agar bagian hasil pada "
            "laporan ini terisi."
        )
    return (
        "Laporan ini merangkum proses diagnosis gangguan internet yang dijalankan "
        "secara deterministik oleh NetExpert. Berdasarkan fakta awal yang dipilih, "
        + "; ".join(parts)
        + ". Seluruh langkah penalaran dicatat dan dapat diverifikasi."
    )


def _knowledge_blocks(rules: Sequence[Rule], initial_facts: Sequence[str]) -> List[dict]:
    blocks: List[dict] = [
        {
            "type": "p",
            "text": (
                "Basis pengetahuan terdiri dari aturan produksi berbentuk IF–THEN. "
                "Setiap aturan memiliki tingkat kepentingan (salience) dan spesifisitas "
                "yang digunakan pada tahap conflict resolution. Aturan dengan operator "
                "AND membutuhkan seluruh kondisi bernilai benar, sedangkan operator OR "
                "cukup membutuhkan minimal satu kondisi benar."
            ),
        }
    ]
    if rules:
        blocks.append(
            {
                "type": "table",
                "headers": ["ID", "Operator", "IF (Kondisi)", "THEN (Kesimpulan)", "Salience"],
                "rows": [
                    [
                        rule.id,
                        rule.connector,
                        rule.joined_conditions,
                        rule.conclusion,
                        f"{rule.salience} ({salience_label(rule.salience)})",
                    ]
                    for rule in rules
                ],
            }
        )
    if initial_facts:
        blocks.append(
            {
                "type": "facts",
                "title": "Fakta awal (working memory)",
                "facts": list(initial_facts),
            }
        )
    return blocks


def _forward_section(forward: ForwardResult) -> dict:
    blocks: List[dict] = []
    fired = " → ".join(forward.fired_rules) if forward.fired_rules else "—"
    paragraph = (
        f"Forward chaining dijalankan atas {len(forward.initial_facts)} fakta awal "
        f"dan berhenti setelah {len(forward.iterations)} iterasi. "
        f"Urutan aturan yang ditembakkan adalah {fired}."
    )
    if forward.terminated_reason:
        paragraph += f" {forward.terminated_reason}"
    blocks.append({"type": "p", "text": paragraph})

    rows: List[List[str]] = []
    for iteration in forward.iterations:
        conflict = ", ".join(iteration.conflict_set) or "—"
        selected = iteration.selected_rule or "STOP"
        conclusion = iteration.conclusion or "—"
        if iteration.conclusion_added is True:
            added = "Ya"
        elif iteration.conclusion_added is False:
            added = "Tidak (sudah ada)"
        else:
            added = "—"
        rows.append(
            [iteration.iteration, conflict, selected, conclusion, added]
        )
    if rows:
        blocks.append(
            {
                "type": "table",
                "headers": [
                    "Iterasi",
                    "Conflict Set",
                    "Aturan Terpilih",
                    "Kesimpulan",
                    "Ditambahkan ke WM",
                ],
                "rows": rows,
            }
        )
    if forward.derived_facts:
        blocks.append(
            {
                "type": "facts",
                "title": "Fakta turunan (derived facts)",
                "facts": list(forward.derived_facts),
            }
        )
    if forward.final_facts:
        blocks.append(
            {
                "type": "facts",
                "title": "Working memory akhir",
                "facts": list(forward.final_facts),
            }
        )
    return {"title": "Hasil Forward Chaining", "blocks": blocks}


def _backward_rows(result: BackwardResult) -> List[List[str]]:
    rows: List[List[str]] = []

    def walk(node: BackwardNode, path: str) -> None:
        current = f"{path} > {node.label}" if path else node.label
        rows.append([current, node.kind, node.status.value])
        for child in node.children:
            walk(child, current)

    walk(result.root, "")
    return rows


def _backward_section(backward: BackwardResult) -> dict:
    blocks: List[dict] = []
    status = "PROVEN" if backward.proven else "UNPROVEN"
    path = " → ".join(backward.proof_path) if backward.proof_path else "—"
    paragraph = (
        f"Backward chaining dimulai dari goal '{backward.goal}'. Status akhir goal "
        f"adalah {status} melalui jalur pembuktian {path}."
    )
    if backward.cycle_detected:
        paragraph += " Terdeteksi siklus pada pohon pembuktian sehingga rekursi dihentikan."
    blocks.append({"type": "p", "text": paragraph})

    rows = _backward_rows(backward)
    if rows:
        blocks.append(
            {
                "type": "table",
                "headers": ["Jalur Pembuktian", "Tipe", "Status"],
                "rows": rows,
            }
        )
    return {"title": "Hasil Backward Chaining", "blocks": blocks}


def _auto_conclusion(forward, backward, rules) -> List[str]:
    items: List[str] = []
    by_id = {rule.id: rule for rule in (rules or [])}
    if forward and forward.fired_rules:
        seen: List[str] = []
        for rule_id in forward.fired_rules:
            rule = by_id.get(rule_id)
            conclusion = rule.conclusion if rule else None
            if conclusion and conclusion not in seen:
                seen.append(conclusion)
        for conclusion in seen:
            items.append(f"Tindakan hasil inferensi: {conclusion}.")
    if forward and forward.derived_facts:
        items.append("Fakta turunan yang diperoleh: " + ", ".join(forward.derived_facts) + ".")
    if backward:
        verdict = "terbukti" if backward.proven else "tidak terbukti"
        detail = (
            f" melalui jalur {', '.join(backward.proof_path)}"
            if backward.proof_path
            else ""
        )
        items.append(f"Goal '{backward.goal}' {verdict}{detail}.")
    return items


def _conclusion_section(meta, forward, backward, rules) -> dict:
    blocks: List[dict] = []
    auto = _auto_conclusion(forward, backward, rules)
    if auto:
        blocks.append({"type": "list", "items": auto})
    if str(meta.conclusion).strip():
        blocks.append({"type": "p", "text": str(meta.conclusion).strip()})
    if not blocks:
        blocks.append(
            {
                "type": "p",
                "text": (
                    "Belum ada hasil inferensi yang dapat disimpulkan. Jalankan "
                    "diagnosis terlebih dahulu, lalu lengkapi bagian ini dengan "
                    "catatan analisis bila diperlukan."
                ),
            }
        )
    return {"title": "Kesimpulan dan Rekomendasi", "blocks": blocks}


def _appendix(forward, backward) -> Optional[dict]:
    blocks: List[dict] = []
    if forward:
        rows: List[List[str]] = []
        for iteration in forward.iterations:
            for evaluation in iteration.evaluations:
                for condition in evaluation.condition_results:
                    rows.append(
                        [
                            iteration.iteration,
                            evaluation.rule_id,
                            evaluation.connector,
                            condition.condition,
                            condition.label,
                        ]
                    )
        if rows:
            blocks.append(
                {
                    "type": "table",
                    "headers": ["Iterasi", "Aturan", "Operator", "Kondisi", "Status"],
                    "rows": rows,
                }
            )
    if backward and backward.log:
        blocks.append(
            {
                "type": "facts",
                "title": "Log pembuktian backward chaining",
                "facts": list(backward.log),
            }
        )
    if not blocks:
        return None
    return {"title": "Lampiran — Jejak Evaluasi Lengkap", "blocks": blocks}


def build_sections(
    meta,
    *,
    forward: Optional[ForwardResult] = None,
    backward: Optional[BackwardResult] = None,
    rules: Optional[Sequence[Rule]] = None,
    initial_facts: Optional[Sequence[str]] = None,
) -> List[dict]:
    """Assemble the numbered body sections shared by every renderer."""
    rules = list(rules or [])
    initial_facts = list(initial_facts or [])

    sections: List[dict] = []

    summary = str(meta.summary).strip() or _auto_summary(forward, backward, rules)
    sections.append(
        {"title": "Ringkasan Eksekutif", "blocks": [{"type": "p", "text": summary}]}
    )

    background = str(meta.background).strip() or _DEFAULT_BACKGROUND
    sections.append(
        {"title": "Pendahuluan", "blocks": [{"type": "p", "text": background}]}
    )

    sections.append(
        {
            "title": "Basis Pengetahuan dan Fakta Awal",
            "blocks": _knowledge_blocks(rules, initial_facts),
        }
    )

    if forward:
        sections.append(_forward_section(forward))
    if backward:
        sections.append(_backward_section(backward))

    sections.append(_conclusion_section(meta, forward, backward, rules))

    appendix = _appendix(forward, backward)
    if appendix:
        sections.append(appendix)

    return sections


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------
_CSS = """
* { box-sizing: border-box; }
html, body { background: #ffffff; }
body {
  margin: 0;
  color: #111111;
  font-family: "Times New Roman", "Liberation Serif", Georgia, serif;
  font-size: 12pt;
  line-height: 1.55;
}
.page { max-width: 820px; margin: 0 auto; padding: 42px 56px; }
.cover { text-align: center; padding-top: 54px; }
.cover .logo { display: block; max-height: 104px; max-width: 240px; margin: 0 auto 26px; }
.cover h1 {
  font-size: 20pt; line-height: 1.32; letter-spacing: 0.5px;
  text-transform: uppercase; margin: 0 0 8px; color: #000000;
}
.cover .sub { font-size: 12.5pt; color: #4b5563; margin-bottom: 10px; }
.cover .inst { font-size: 12pt; font-weight: bold; margin-bottom: 28px; }
.cover .rule { width: 120px; height: 2px; background: #000000; margin: 0 auto 28px; }
.identity { border-collapse: collapse; margin: 0 auto; text-align: left; width: 100%; max-width: 600px; }
.identity td { padding: 4px 8px; vertical-align: top; font-size: 11.5pt; }
.identity td.k { width: 35%; color: #4b5563; }
.identity td.v { font-weight: 600; }
.identity ol.members { margin: 0; padding-left: 1.1rem; font-weight: 600; }
.identity ol.members li { margin: 2px 0; }
h2.section {
  font-size: 13pt; text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 1.6px solid #000000; padding-bottom: 4px; margin: 26px 0 12px;
  color: #000000;
}
p { margin: 0 0 10px; text-align: justify; }
table.data { width: 100%; border-collapse: collapse; margin: 6px 0 16px; font-size: 10.5pt; }
table.data th, table.data td {
  border: 1px solid #000000; padding: 5px 8px; text-align: left; vertical-align: top;
}
table.data th { background: #f0f0f0; font-weight: bold; }
.facts-title { font-weight: bold; margin: 12px 0 4px; }
ul.facts, ul.plain { margin: 0 0 12px; padding-left: 1.35rem; }
ul.facts li, ul.plain li { margin: 2px 0; }
.signature { margin-top: 46px; display: flex; justify-content: flex-end; }
.signature .box { text-align: center; min-width: 280px; }
.signature .space { height: 64px; }
.signature .name { font-weight: bold; text-decoration: underline; }
.note { font-size: 10pt; color: #4b5563; font-style: italic; margin-top: 26px; }
@page { size: A4; margin: 18mm 16mm; }
@media print {
  .page { max-width: none; padding: 0 0 18px 0; break-after: page; }
  .page:last-child { break-after: auto; }
  h2.section { break-after: avoid; }
  tr, li { break-inside: avoid; }
}
"""


def _html_block(block: dict) -> str:
    kind = block.get("type")
    if kind == "p":
        return f'<p>{_esc(block.get("text", ""))}</p>'
    if kind == "list":
        items = "".join(f"<li>{_esc(item)}</li>" for item in block.get("items", []))
        return f'<ul class="plain">{items}</ul>'
    if kind == "facts":
        title = f'<div class="facts-title">{_esc(block.get("title", ""))}</div>'
        items = "".join(f"<li>{_esc(item)}</li>" for item in block.get("facts", []))
        return f'{title}<ul class="facts">{items}</ul>'
    if kind == "table":
        headers = "".join(f"<th>{_esc(h)}</th>" for h in block.get("headers", []))
        rows = "".join(
            "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>"
            for row in block.get("rows", [])
        )
        return (
            f'<table class="data"><thead><tr>{headers}</tr></thead>'
            f"<tbody>{rows}</tbody></table>"
        )
    return ""


def _html_cover(cover: dict) -> str:
    logo = (
        f'<img class="logo" src="{_esc(cover["logo"])}" alt="Logo institusi"/>'
        if cover.get("logo")
        else ""
    )
    subtitle = f'<div class="sub">{_esc(cover["subtitle"])}</div>' if cover["subtitle"] else ""
    institution = f'<div class="inst">{_esc(cover["institution"])}</div>' if cover["institution"] else ""

    rows = "".join(
        f'<tr><td class="k">{_esc(label)}</td><td class="v">{_esc(value)}</td></tr>'
        for label, value in cover["identity"]
    )
    members = ""
    if cover["members"]:
        items = "".join(f"<li>{_esc(member)}</li>" for member in cover["members"])
        members = (
            '<tr><td class="k">Anggota Kelompok</td>'
            f'<td class="v"><ol class="members">{items}</ol></td></tr>'
        )
    identity = f'<table class="identity">{rows}{members}</table>' if (rows or members) else ""

    return (
        '<section class="page cover">'
        f"{logo}<h1>{_esc(cover['title'])}</h1>"
        f'{subtitle}{institution}<div class="rule"></div>{identity}'
        "</section>"
    )


def _html_signature(meta, generated_at: str) -> str:
    members = meta.real_members
    if members:
        primary = members[0]
        name = str(primary.name).strip() or "—"
        nim = f"NIM {primary.nim.strip()}" if str(primary.nim).strip() else ""
    else:
        name = meta.group_label or str(meta.institution).strip() or "—"
        nim = ""

    place_date = ""
    city = str(meta.city).strip()
    date = str(meta.date).strip()
    if city and date:
        place_date = f"{city}, {date}"
    elif city:
        place_date = city
    elif date:
        place_date = date

    return (
        '<section class="page">'
        '<div class="signature"><div class="box">'
        f"<div>{_esc(place_date)}</div>"
        "<div>Penyusun,</div>"
        '<div class="space"></div>'
        f'<div class="name">{_esc(name)}</div>'
        f"<div>{_esc(nim)}</div>"
        "</div></div>"
        f'<div class="note">Dokumen ini dihasilkan otomatis oleh NetExpert pada '
        f"{_esc(generated_at)}.</div>"
        "</section>"
    )


def render_html(
    meta,
    *,
    forward: Optional[ForwardResult] = None,
    backward: Optional[BackwardResult] = None,
    rules: Optional[Sequence[Rule]] = None,
    initial_facts: Optional[Sequence[str]] = None,
    generated_at: str = "",
) -> str:
    """Return a complete, self-contained, print-ready HTML document."""
    cover = build_cover(meta)
    sections = build_sections(
        meta,
        forward=forward,
        backward=backward,
        rules=rules,
        initial_facts=initial_facts,
    )

    body: List[str] = [_html_cover(cover)]
    for index, section in enumerate(sections, 1):
        blocks = "".join(_html_block(block) for block in section["blocks"])
        body.append(
            f'<section class="page"><h2 class="section">{index}. '
            f'{_esc(section["title"])}</h2>{blocks}</section>'
        )
    body.append(_html_signature(meta, generated_at))

    return (
        "<!doctype html>\n<html lang=\"id\">\n<head>\n"
        '<meta charset="utf-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f"<title>{_esc(cover['title'])}</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------
def _md_blocks(blocks: Sequence[dict]) -> List[str]:
    lines: List[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "p":
            lines.append(str(block.get("text", "")))
            lines.append("")
        elif kind == "list":
            lines.extend(f"- {item}" for item in block.get("items", []))
            lines.append("")
        elif kind == "facts":
            lines.append(f"**{block.get('title', '')}**")
            lines.append("")
            lines.extend(f"- {item}" for item in block.get("facts", []))
            lines.append("")
        elif kind == "table":
            headers = block.get("headers", [])
            lines.append("| " + " | ".join(_md_cell(h) for h in headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in block.get("rows", []):
                lines.append("| " + " | ".join(_md_cell(cell) for cell in row) + " |")
            lines.append("")
    return lines


def render_markdown(
    meta,
    *,
    forward: Optional[ForwardResult] = None,
    backward: Optional[BackwardResult] = None,
    rules: Optional[Sequence[Rule]] = None,
    initial_facts: Optional[Sequence[str]] = None,
    generated_at: str = "",
) -> str:
    """Return the same report as plain Markdown (easy to paste into docs)."""
    cover = build_cover(meta)
    sections = build_sections(
        meta,
        forward=forward,
        backward=backward,
        rules=rules,
        initial_facts=initial_facts,
    )

    lines: List[str] = [f"# {cover['title']}", ""]
    if cover["subtitle"]:
        lines.append(f"_{cover['subtitle']}_")
        lines.append("")
    if cover["institution"]:
        lines.append(f"**{cover['institution']}**")
        lines.append("")
    for label, value in cover["identity"]:
        lines.append(f"- **{label}:** {value}")
    if cover["members"]:
        lines.append("- **Anggota Kelompok:**")
        lines.extend(f"    - {member}" for member in cover["members"])
    if cover["identity"] or cover["members"]:
        lines.append("")

    for index, section in enumerate(sections, 1):
        lines.append(f"## {index}. {section['title']}")
        lines.append("")
        lines.extend(_md_blocks(section["blocks"]))

    lines.append("---")
    lines.append("")
    members = meta.real_members
    if members:
        lines.append(f"Penyusun: {members[0].one_line()}")
    elif meta.group_label:
        lines.append(f"Penyusun: {meta.group_label}")
    if generated_at:
        lines.append("")
        lines.append(f"_Dokumen ini dihasilkan otomatis oleh NetExpert pada {generated_at}._")

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "build_cover",
    "build_sections",
    "render_html",
    "render_markdown",
]
