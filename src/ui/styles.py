"""Global white-first styling for the NetExpert Streamlit interface."""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --background: #FFFFFF;
  --surface: #F8FAFC;
  --surface-hover: #F1F5F9;
  --border: #E2E8F0;
  --text-primary: #0F172A;
  --text-secondary: #64748B;
  --primary: #2563EB;
  --primary-hover: #1D4ED8;
  --success: #16A34A;
  --success-soft: #F0FDF4;
  --danger: #DC2626;
  --danger-soft: #FEF2F2;
  --warning: #D97706;
  --warning-soft: #FFFBEB;
  --neutral: #64748B;
}

html, body, [class*="st-"], .stApp, button, input, textarea, select {
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}
/* The Inter rule above also matches Streamlit's emotion classes on icon
   spans, which turns Material ligatures (e.g. "keyboard_arrow_right") into
   literal text.  Restore the icon font with higher specificity. */
html body [data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Rounded' !important;
  font-weight: 400 !important;
  font-style: normal !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  white-space: nowrap !important;
  direction: ltr !important;
  font-feature-settings: 'liga' !important;
  -webkit-font-feature-settings: 'liga' !important;
  -webkit-font-smoothing: antialiased !important;
}

.stApp { background: var(--background); }
/* Solid header: content scrolls underneath it, but the first screen starts below it. */
[data-testid="stHeader"] { background: #FFFFFF; backdrop-filter: none; }
#MainMenu, footer { visibility: hidden; }

.block-container {
  padding-top: 3.9rem; /* clears the 60px fixed header */
  padding-bottom: 3.5rem;
  max-width: 1240px;
}

h1, h2, h3, h4 { color: var(--text-primary); letter-spacing: -0.02em; }
p, li, span, label { color: var(--text-primary); }
small, .nx-muted { color: var(--text-secondary); }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: #FFFFFF;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
[data-testid="stSidebar"] .block-container { padding-top: 0.5rem; }

.nx-brand { display: flex; align-items: center; gap: 0.7rem; padding: 0.1rem 0.35rem 1.1rem 0.35rem; }
.nx-brand-mark {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%);
  border: 1px solid #BFDBFE;
}
.nx-brand-name { font-size: 1.02rem; font-weight: 700; color: var(--text-primary); line-height: 1.15; }
.nx-brand-sub { font-size: 0.68rem; color: var(--text-secondary); letter-spacing: 0.03em; text-transform: uppercase; }
.nx-side-label {
  font-size: 0.66rem; font-weight: 600; letter-spacing: 0.09em;
  text-transform: uppercase; color: #94A3B8;
  padding: 0.2rem 0.6rem 0.4rem 0.6rem;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] { gap: 0.1rem; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div { width: 100%; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
  width: 100%;
  padding: 0.5rem 0.62rem;
  border-radius: 8px;
  border: 1px solid transparent;
  margin: 0.08rem 0;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background: var(--surface); }
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
  font-size: 0.88rem; font-weight: 500; line-height: 1.2;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
  background: #EFF6FF;
  border-color: #DBEAFE;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {
  color: var(--primary); font-weight: 600;
}
/* Hide the default radio bullet; the highlighted row is the selection cue. */
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {
  display: none;
}

/* Keep the sidebar toggle readable even if the icon font is unavailable. */
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
[data-testid="collapsedControl"] [data-testid="stIconMaterial"] {
  font-size: 0 !important;
}
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::after {
  content: "";
  display: inline-block;
  width: 7px; height: 7px;
  border-left: 2px solid #64748B;
  border-bottom: 2px solid #64748B;
  transform: rotate(45deg);
  margin: 0 4px 2px 2px;
}
[data-testid="collapsedControl"] [data-testid="stIconMaterial"]::after {
  content: "";
  display: inline-block;
  width: 7px; height: 7px;
  border-right: 2px solid #64748B;
  border-top: 2px solid #64748B;
  transform: rotate(45deg);
  margin: 0 2px 0 4px;
}

.nx-side-footer {
  margin-top: 1.4rem; padding: 0.9rem 0.65rem 0.2rem 0.65rem;
  border-top: 1px solid var(--border);
  font-size: 0.7rem; color: var(--text-secondary);
  display: flex; align-items: center; gap: 0.45rem;
}
.nx-status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--success); display: inline-block;
  box-shadow: 0 0 0 3px var(--success-soft);
}

/* ---------- Buttons ---------- */
.stButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
  border-radius: 8px;
  font-weight: 550;
  font-size: 0.86rem;
  padding: 0.42rem 0.9rem;
  border: 1px solid var(--border);
  transition: all 120ms ease;
  box-shadow: none;
}
.stButton > button:hover { border-color: #CBD5E1; background: var(--surface); }
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
  background: var(--primary) !important;
  border-color: var(--primary) !important;
  color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
  background: var(--primary-hover) !important;
  border-color: var(--primary-hover) !important;
}
[data-testid="stBaseButton-primary"] p { color: #FFFFFF !important; }

/* ---------- Inputs ---------- */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  border-radius: 8px !important;
  border-color: var(--border) !important;
  font-size: 0.88rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.10) !important;
}
[data-baseweb="select"] > div {
  border-radius: 8px !important;
  border-color: var(--border) !important;
}

/* ---------- Cards & layout ---------- */
.nx-hero {
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 1.55rem 1.7rem;
  background:
    radial-gradient(circle at 100% 0%, #EFF6FF 0%, rgba(239,246,255,0) 45%),
    #FFFFFF;
  margin-bottom: 1.15rem;
}
.nx-eyebrow {
  font-size: 0.68rem; font-weight: 650; letter-spacing: 0.11em;
  text-transform: uppercase; color: var(--primary);
  margin-bottom: 0.45rem;
}
.nx-hero h1 { font-size: 1.72rem; font-weight: 700; margin: 0 0 0.35rem 0; line-height: 1.2; }
.nx-hero p { color: var(--text-secondary); font-size: 0.92rem; margin: 0; max-width: 760px; line-height: 1.55; }

.nx-page-head { margin-bottom: 1.1rem; }
.nx-page-head h2 { font-size: 1.4rem; font-weight: 700; margin: 0 0 0.2rem 0; }
.nx-page-head p { color: var(--text-secondary); font-size: 0.88rem; margin: 0; }

.nx-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #FFFFFF;
  padding: 1.05rem 1.15rem;
  margin-bottom: 0.9rem;
  box-shadow: 0 1px 2px rgba(15,23,42,0.03);
}
.nx-card-title {
  font-size: 0.95rem; font-weight: 650; color: var(--text-primary);
  margin: 0 0 0.15rem 0;
}
.nx-card-sub { font-size: 0.78rem; color: var(--text-secondary); margin: 0 0 0.7rem 0; }

.nx-metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.05rem;
}
.nx-metric {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #FFFFFF;
  padding: 0.95rem 1.05rem;
  box-shadow: 0 1px 2px rgba(15,23,42,0.03);
}
.nx-metric-label {
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.07em;
  text-transform: uppercase; color: var(--text-secondary);
  margin-bottom: 0.4rem;
}
.nx-metric-value { font-size: 1.65rem; font-weight: 700; color: var(--text-primary); line-height: 1; }
.nx-metric-hint { font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.35rem; }
.nx-metric.accent-blue { border-top: 2px solid var(--primary); }
.nx-metric.accent-green { border-top: 2px solid var(--success); }
.nx-metric.accent-amber { border-top: 2px solid var(--warning); }
.nx-metric.accent-red { border-top: 2px solid var(--danger); }

/* ---------- Badges & chips ---------- */
.nx-badge {
  display: inline-flex; align-items: center; gap: 0.28rem;
  font-size: 0.66rem; font-weight: 650; letter-spacing: 0.04em;
  text-transform: uppercase; padding: 0.16rem 0.48rem;
  border-radius: 999px; border: 1px solid transparent; white-space: nowrap;
}
.nx-badge.green { background: var(--success-soft); color: #15803D; border-color: #BBF7D0; }
.nx-badge.red { background: var(--danger-soft); color: #B91C1C; border-color: #FECACA; }
.nx-badge.amber { background: var(--warning-soft); color: #B45309; border-color: #FDE68A; }
.nx-badge.blue { background: #EFF6FF; color: #1D4ED8; border-color: #BFDBFE; }
.nx-badge.gray { background: var(--surface); color: var(--text-secondary); border-color: var(--border); }

.nx-chip {
  display: inline-block; padding: 0.24rem 0.6rem; margin: 0.14rem 0.22rem 0.14rem 0;
  border-radius: 7px; font-size: 0.76rem; font-weight: 500;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-primary);
}
.nx-chip.blue { background: #EFF6FF; border-color: #DBEAFE; color: #1E40AF; }
.nx-chip.green { background: var(--success-soft); border-color: #BBF7D0; color: #15803D; }
.nx-chip.amber { background: var(--warning-soft); border-color: #FDE68A; color: #B45309; }
.nx-chip.red { background: var(--danger-soft); border-color: #FECACA; color: #B91C1C; }
.nx-chip.gray { background: var(--surface); border-color: var(--border); color: var(--text-secondary); }
.nx-chip.mono { font-variant-numeric: tabular-nums; font-weight: 600; }

/* ---------- Tables ---------- */
.nx-table-wrap { border: 1px solid var(--border); border-radius: 11px; overflow: hidden; margin: 0.4rem 0 0.6rem 0; }
table.nx-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #FFFFFF; }
table.nx-table thead th {
  text-align: left; padding: 0.55rem 0.7rem; background: var(--surface);
  color: var(--text-secondary); font-size: 0.68rem; font-weight: 650;
  letter-spacing: 0.06em; text-transform: uppercase;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
table.nx-table tbody td {
  padding: 0.58rem 0.7rem; border-bottom: 1px solid #F1F5F9;
  vertical-align: top; color: var(--text-primary);
}
table.nx-table tbody tr:last-child td { border-bottom: none; }
table.nx-table tbody tr:hover { background: #FCFDFF; }
.nx-num { font-variant-numeric: tabular-nums; }
.nx-cond-list { margin: 0; padding: 0; list-style: none; }
.nx-cond-list li { padding: 0.13rem 0; font-size: 0.8rem; }
.nx-cond-list .nx-badge { margin-right: 0.4rem; }

/* ---------- Status banner ---------- */
.nx-banner {
  display: flex; gap: 0.85rem; align-items: flex-start;
  border-radius: 12px; padding: 1rem 1.15rem; margin: 0.5rem 0 1rem 0;
  border: 1px solid var(--border); background: var(--surface);
}
.nx-banner.green { background: var(--success-soft); border-color: #BBF7D0; }
.nx-banner.red { background: var(--danger-soft); border-color: #FECACA; }
.nx-banner.amber { background: var(--warning-soft); border-color: #FDE68A; }
.nx-banner.blue { background: #EFF6FF; border-color: #DBEAFE; }
.nx-banner-icon {
  width: 30px; height: 30px; border-radius: 8px; flex: 0 0 30px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.9rem; background: #FFFFFF;
  border: 1px solid rgba(15,23,42,0.08);
}
.nx-banner.green .nx-banner-icon { color: var(--success); }
.nx-banner.red .nx-banner-icon { color: var(--danger); }
.nx-banner.amber .nx-banner-icon { color: var(--warning); }
.nx-banner.blue .nx-banner-icon { color: var(--primary); }
.nx-banner-title { font-size: 0.9rem; font-weight: 650; margin-bottom: 0.12rem; }
.nx-banner-msg { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; }

/* ---------- Empty state ---------- */
.nx-empty {
  border: 1px dashed #CBD5E1; border-radius: 12px; background: #FCFDFF;
  padding: 2.1rem 1.4rem; text-align: center; margin: 0.5rem 0 1rem 0;
}
.nx-empty-title { font-size: 0.96rem; font-weight: 650; color: var(--text-primary); margin-bottom: 0.3rem; }
.nx-empty-msg { font-size: 0.82rem; color: var(--text-secondary); max-width: 520px; margin: 0 auto; line-height: 1.55; }

/* ---------- Evaluation cards ---------- */
.nx-eval {
  border: 1px solid var(--border); border-radius: 10px;
  padding: 0.7rem 0.85rem; margin: 0.45rem 0; background: #FFFFFF;
}
.nx-eval-head { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.35rem; }
.nx-eval-id { font-weight: 700; font-size: 0.86rem; }
.nx-eval-meta { font-size: 0.72rem; color: var(--text-secondary); }
.nx-eval-reason { font-size: 0.76rem; color: var(--text-secondary); margin-top: 0.4rem; line-height: 1.45; }
.nx-cond-row { display: flex; align-items: center; gap: 0.45rem; padding: 0.16rem 0; font-size: 0.79rem; }
.nx-cond-name { color: var(--text-primary); }

/* ---------- Iteration ---------- */
.nx-iter-head { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
.nx-iter-title { font-weight: 650; font-size: 0.92rem; }
.nx-kv { font-size: 0.78rem; color: var(--text-secondary); }
.nx-kv b { color: var(--text-primary); font-weight: 600; }

/* ---------- Steps / pipeline ---------- */
.nx-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 0.7rem; margin-top: 0.4rem; }
.nx-step { border: 1px solid var(--border); border-radius: 10px; padding: 0.8rem 0.9rem; background: var(--surface); }
.nx-step-num { font-size: 0.66rem; font-weight: 700; color: var(--primary); letter-spacing: 0.08em; margin-bottom: 0.28rem; }
.nx-step-title { font-size: 0.83rem; font-weight: 600; margin-bottom: 0.18rem; }
.nx-step-desc { font-size: 0.74rem; color: var(--text-secondary); line-height: 1.45; }

/* ---------- Streamlit widgets ---------- */
/* Hide deploy/menu chrome so the app reads as a product surface, but keep the
   toolbar container: it hosts the "expand sidebar" control when collapsed. */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] {
  display: none !important;
}

/* Reopen control shown only while the sidebar is collapsed. */
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
  font-size: 0 !important;
}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]::after {
  content: "";
  display: inline-block;
  width: 7px; height: 7px;
  border-right: 2px solid #64748B;
  border-top: 2px solid #64748B;
  transform: rotate(45deg);
  margin: 0 2px 0 2px;
}

/* Sidebar popover button: hide the material ligature and let the label fit. */
[data-testid="stPopoverButton"] [data-testid="stIconMaterial"] { display: none !important; }
[data-testid="stSidebar"] [data-testid="stPopoverButton"] { font-size: 0.8rem; }
[data-testid="stSidebar"] [data-testid="stPopoverButton"] p { font-size: 0.8rem; }

/* Multiselect selected facts as soft blue tags. */
[data-testid="stMultiSelectTagsContainer"] > span[role="group"] {
  flex-wrap: wrap !important;
  row-gap: 0.2rem;
}
[data-testid="stMultiSelectTagsContainer"] [data-tag] {
  background: #EFF6FF !important;
  border: 1px solid #DBEAFE !important;
  border-radius: 6px !important;
  padding: 0.08rem 0.4rem !important;
  font-size: 0.73rem !important;
  color: #1E40AF !important;
}
[data-testid="stMultiSelectTagsContainer"] [data-tag] span,
[data-testid="stMultiSelectTagsContainer"] [data-tag] button {
  color: #1E40AF !important;
  font-size: 0.73rem !important;
}
[data-testid="stMultiSelectTagsContainer"] [data-tag] svg { stroke: #1E40AF !important; }

[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  background: #FFFFFF;
  box-shadow: none !important;
  margin-bottom: 0.55rem;
}
[data-testid="stExpander"] summary { font-size: 0.85rem; font-weight: 550; }
.stTabs [data-baseweb="tab-list"] { gap: 0.25rem; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { font-size: 0.86rem; font-weight: 550; padding: 0.5rem 0.8rem; }
.stTabs [aria-selected="true"] { color: var(--primary); }

[data-testid="stAlert"] { border-radius: 10px; font-size: 0.82rem; }
[data-testid="stGraphvizChart"] {
  border: 1px solid var(--border); border-radius: 12px; background: #FFFFFF;
  padding: 0.4rem; overflow: auto;
}
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; }

/* Hide the "Press Enter to apply" helper clutter */
[data-testid="InputInstructions"] { visibility: hidden; }

/* Responsive */
@media (max-width: 900px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .nx-hero { padding: 1.2rem 1.15rem; }
  .nx-hero h1 { font-size: 1.42rem; }
}
</style>
"""


def inject_styles() -> None:
    """Inject the global stylesheet once per rerun."""
    st.markdown(CSS, unsafe_allow_html=True)