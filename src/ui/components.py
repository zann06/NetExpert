"""Reusable HTML components for the NetExpert interface."""

from __future__ import annotations

import html
from typing import Iterable, List, Sequence

import streamlit as st

from ..models import (
    ConditionEvaluation,
    IterationTrace,
    NodeStatus,
    Rule,
    RuleEvaluation,
    RuleStatus,
    salience_label,
)

# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------
def esc(value) -> str:
    return html.escape(str(value))


TONE_BY_RULE_STATUS = {
    RuleStatus.FIRED: "green",
    RuleStatus.NOT_READY: "red",
    RuleStatus.READY_NOT_SELECTED: "amber",
    RuleStatus.READY: "amber",
    RuleStatus.REFRACTORY: "gray",
}

TONE_BY_NODE_STATUS = {
    NodeStatus.TRUE: "green",
    NodeStatus.PROVEN: "green",
    NodeStatus.FIRED: "green",
    NodeStatus.FALSE: "red",
    NodeStatus.UNPROVEN: "red",
    NodeStatus.NOT_READY: "red",
    NodeStatus.READY: "amber",
    NodeStatus.READY_NOT_SELECTED: "amber",
    NodeStatus.CYCLE: "amber",
    NodeStatus.REFRACTORY: "gray",
    NodeStatus.NEUTRAL: "gray",
}


def badge(text: str, tone: str = "gray") -> str:
    return f'<span class="nx-badge {esc(tone)}">{esc(text)}</span>'


def chip(text: str, tone: str = "gray", mono: bool = False) -> str:
    extra = " mono" if mono else ""
    return f'<span class="nx-chip {esc(tone)}{extra}">{esc(text)}</span>'


def chips(facts: Iterable[str], tone: str = "gray") -> str:
    return "".join(chip(fact, tone) for fact in facts) or '<span class="nx-muted">—</span>'


def html_block(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------
def brand() -> None:
    html_block(
        '<div class="nx-brand">'
        '<div class="nx-brand-mark">'
        '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="12" cy="12" r="2.2" fill="#2563EB"/>'
        '<path d="M12 3.5v3.2M12 17.3v3.2M3.5 12h3.2M17.3 12h3.2" '
        'stroke="#2563EB" stroke-width="1.6" stroke-linecap="round"/>'
        '<circle cx="12" cy="4.4" r="1.1" fill="#2563EB"/>'
        '<circle cx="12" cy="19.6" r="1.1" fill="#2563EB"/>'
        '<circle cx="4.4" cy="12" r="1.1" fill="#2563EB"/>'
        '<circle cx="19.6" cy="12" r="1.1" fill="#2563EB"/>'
        "</svg></div>"
        '<div><div class="nx-brand-name">NetExpert</div>'
        '<div class="nx-brand-sub">Expert System</div></div></div>'
    )


def sidebar_footer() -> None:
    html_block(
        '<div class="nx-side-footer">'
        '<span class="nx-status-dot"></span>'
        "<span>Engine ready · v1.0.0</span></div>"
    )


def hero(eyebrow: str, title: str, subtitle: str) -> None:
    html_block(
        f'<div class="nx-hero"><div class="nx-eyebrow">{esc(eyebrow)}</div>'
        f"<h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>"
    )


def page_head(title: str, subtitle: str = "") -> None:
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    html_block(f'<div class="nx-page-head"><h2>{esc(title)}</h2>{sub}</div>')


def section_title(title: str, subtitle: str = "") -> None:
    sub = f'<div class="nx-card-sub">{esc(subtitle)}</div>' if subtitle else ""
    html_block(f'<div class="nx-card-title">{esc(title)}</div>{sub}')


def banner(tone: str, title: str, message: str = "", icon: str = "") -> None:
    symbols = {"green": "✓", "red": "✕", "amber": "!", "blue": "i", "gray": "·"}
    icon = icon or symbols.get(tone, "·")
    msg = f'<div class="nx-banner-msg">{esc(message)}</div>' if message else ""
    html_block(
        f'<div class="nx-banner {esc(tone)}"><div class="nx-banner-icon">{esc(icon)}</div>'
        f'<div><div class="nx-banner-title">{esc(title)}</div>{msg}</div></div>'
    )


def empty_state(title: str, message: str) -> None:
    html_block(
        f'<div class="nx-empty"><div class="nx-empty-title">{esc(title)}</div>'
        f'<div class="nx-empty-msg">{esc(message)}</div></div>'
    )


def metric_grid(items: Sequence[dict]) -> None:
    """Render a responsive grid of metric cards.

    Each item: ``{"label", "value", "hint"?, "accent"?}``.
    """
    cards = []
    for item in items:
        accent = item.get("accent", "blue")
        hint = (
            f'<div class="nx-metric-hint">{esc(item["hint"])}</div>'
            if item.get("hint")
            else ""
        )
        cards.append(
            f'<div class="nx-metric accent-{esc(accent)}">'
            f'<div class="nx-metric-label">{esc(item["label"])}</div>'
            f'<div class="nx-metric-value">{esc(item["value"])}</div>'
            f"{hint}</div>"
        )
    html_block(f'<div class="nx-metric-grid">{"".join(cards)}</div>')


def steps(items: Sequence[tuple]) -> None:
    """items: list of (number, title, description)."""
    cards = "".join(
        f'<div class="nx-step"><div class="nx-step-num">{esc(num)}</div>'
        f'<div class="nx-step-title">{esc(title)}</div>'
        f'<div class="nx-step-desc">{esc(desc)}</div></div>'
        for num, title, desc in items
    )
    html_block(f'<div class="nx-steps">{cards}</div>')


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def rules_table(rules: Sequence[Rule], show_actions: bool = False) -> str:
    rows = []
    for rule in rules:
        conditions = "".join(
            f'<li>{chip(condition, "blue")}</li>' for condition in rule.conditions
        )
        rows.append(
            "<tr>"
            f'<td><strong>{esc(rule.id)}</strong></td>'
            f'<td>{chip(rule.connector, "gray", mono=True)}</td>'
            f'<td><ul class="nx-cond-list">{conditions}</ul></td>'
            f'<td>{chip(rule.conclusion, "green")}</td>'
            f'<td class="nx-num">{rule.salience} '
            f'<span class="nx-muted">({esc(salience_label(rule.salience))})</span></td>'
            f'<td class="nx-num">{rule.specificity}</td>'
            "</tr>"
        )
    head = (
        "<tr><th>ID</th><th>Logika</th><th>IF</th><th>THEN</th>"
        "<th>Salience</th><th>Spesifisitas</th></tr>"
    )
    return (
        '<div class="nx-table-wrap"><table class="nx-table">'
        f"<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def ranking_table(rows: Sequence[dict]) -> str:
    body = []
    for row in rows:
        position = row["peringkat"]
        badge_html = badge("SELECTED", "green") if position == 1 else ""
        body.append(
            "<tr>"
            f'<td class="nx-num">{position}</td>'
            f'<td><strong>{esc(row["id"])}</strong> {badge_html}</td>'
            f'<td class="nx-num">{row["salience"]} '
            f'<span class="nx-muted">({esc(row["salience_label"])})</span></td>'
            f'<td class="nx-num">{row["specificity"]}</td>'
            f'<td class="nx-num">{row["rule_number"]}</td>'
            f"<td>{esc(row['reason'])}</td>"
            "</tr>"
        )
    head = (
        "<tr><th>#</th><th>Aturan</th><th>Salience</th><th>Spesifisitas</th>"
        "<th>Nomor</th><th>Alasan urutan</th></tr>"
    )
    return (
        '<div class="nx-table-wrap"><table class="nx-table">'
        f"<thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"
    )


# ---------------------------------------------------------------------------
# Forward-chaining evaluation rendering
# ---------------------------------------------------------------------------
def _condition_rows(conditions: Sequence[ConditionEvaluation]) -> str:
    if not conditions:
        return '<div class="nx-eval-reason">Tidak dievaluasi ulang (refractoriness).</div>'
    rows = []
    for condition in conditions:
        tone = "green" if condition.status else "red"
        rows.append(
            f'<div class="nx-cond-row">{badge(condition.label, tone)}'
            f'<span class="nx-cond-name">{esc(condition.condition)}</span></div>'
        )
    return "".join(rows)


def evaluation_card(evaluation: RuleEvaluation) -> str:
    tone = TONE_BY_RULE_STATUS.get(evaluation.status, "gray")
    return (
        '<div class="nx-eval">'
        '<div class="nx-eval-head">'
        f'<span class="nx-eval-id">{esc(evaluation.rule_id)}</span>'
        f"{badge(evaluation.status.label, tone)}"
        f'<span class="nx-eval-meta">salience {evaluation.salience} '
        f'({esc(salience_label(evaluation.salience))}) · '
        f"{evaluation.specificity} kondisi · "
        f"{esc(evaluation.connector)}</span>"
        "</div>"
        f"{_condition_rows(evaluation.condition_results)}"
        f'<div class="nx-eval-reason">{esc(evaluation.reason)}</div>'
        "</div>"
    )


def evaluation_cards(evaluations: Iterable[RuleEvaluation]) -> str:
    return "".join(evaluation_card(ev) for ev in evaluations)


def iteration_heading(iteration: IterationTrace) -> str:
    if iteration.selected_rule:
        title = f"Iterasi {iteration.iteration}"
        right = (
            f"{badge('FIRED ' + iteration.selected_rule, 'green')}"
            f'<span class="nx-kv">menghasilkan <b>{esc(iteration.conclusion or "")}</b></span>'
        )
    else:
        title = f"Iterasi {iteration.iteration}"
        right = badge("STOP — conflict set kosong", "gray")
    return f'<div class="nx-iter-head"><span class="nx-iter-title">{esc(title)}</span>{right}</div>'


def iteration_detail(iteration: IterationTrace, ranking_rows: Sequence[dict]) -> str:
    """Full HTML body for one iteration (snapshot, conflict set, evaluations)."""
    from ..inference.conflict_resolution import describe_ranking  # local import

    parts = [iteration_heading(iteration)]
    parts.append(
        '<div class="nx-kv" style="margin-bottom:0.3rem"><b>Working memory sebelum firing</b></div>'
        f'<div style="margin-bottom:0.65rem">{chips(iteration.facts_before, "blue")}</div>'
    )

    if iteration.conflict_set:
        parts.append(
            '<div class="nx-kv" style="margin-bottom:0.3rem"><b>Conflict set & ranking</b></div>'
        )
        parts.append(ranking_table(ranking_rows))
        parts.append(
            f'<div class="nx-eval-reason" style="margin-bottom:0.55rem">'
            f"<b>Alasan pemilihan:</b> {esc(iteration.selection_reason)}</div>"
        )
    else:
        parts.append(
            '<div class="nx-eval-reason" style="margin-bottom:0.55rem">'
            "<b>Conflict set kosong.</b> Tidak ada aturan yang siap — inferensi berhenti.</div>"
        )

    parts.append(
        '<div class="nx-kv" style="margin-bottom:0.3rem"><b>Evaluasi seluruh aturan</b></div>'
    )
    parts.append(evaluation_cards(iteration.evaluations))

    if iteration.selected_rule:
        added = (
            "ditambahkan ke working memory"
            if iteration.conclusion_added
            else "sudah ada di working memory — tidak diduplikasi"
        )
        parts.append(
            f'<div class="nx-eval-reason"><b>Kesimpulan:</b> '
            f"{chip(iteration.conclusion or '', 'green')} — {esc(added)}</div>"
        )
    parts.append(
        '<div class="nx-kv" style="margin-top:0.45rem"><b>Working memory setelah firing</b></div>'
        f'<div>{chips(iteration.facts_after, "gray")}</div>'
    )
    return "".join(parts)


def backward_rows_table(rows: Sequence[dict]) -> str:
    body = []
    for row in rows:
        status = row["Status"]
        tone = "green" if status in {"PROVEN", "TRUE"} else (
            "amber" if status == "CYCLE" else "red" if status == "UNPROVEN" else "gray"
        )
        body.append(
            "<tr>"
            f'<td>{esc(row["Jalur"])}</td>'
            f'<td>{esc(row["Tipe"])}</td>'
            f"<td>{badge(status, tone)}</td>"
            f'<td>{esc(row["Keterangan"])}</td>'
            "</tr>"
        )
    head = "<tr><th>Jalur</th><th>Tipe</th><th>Status</th><th>Keterangan</th></tr>"
    return (
        '<div class="nx-table-wrap"><table class="nx-table">'
        f"<thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def legend_html() -> None:
    items = [
        ("Fakta / Working Memory", "blue"),
        ("TRUE / PROVEN / FIRED", "green"),
        ("FALSE / UNPROVEN", "red"),
        ("READY / sedang dievaluasi", "amber"),
        ("Refractory / netral", "gray"),
    ]
    body = "".join(
        f'<div style="display:flex;align-items:center;gap:0.45rem;margin:0.18rem 0">'
        f'<span class="nx-chip {tone}" style="width:16px;height:16px;padding:0;'
        f'border-radius:4px;display:inline-block"></span>'
        f'<span style="font-size:0.78rem;color:#475569">{esc(label)}</span></div>'
        for label, tone in items
    )
    html_block(
        '<div class="nx-card" style="padding:0.85rem 1rem">'
        '<div class="nx-metric-label">Legenda</div>'
        f"{body}</div>"
    )