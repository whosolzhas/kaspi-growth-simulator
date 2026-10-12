"""
Kaspi.kz: Growth & Unit Economics Simulator (KZ standalone, 2026E)

Single source of truth: Kaspi_Financial_Analysis.xlsx (Analysis sheet, rows 66-103).
Every formula below mirrors the Excel model; the "Model Integrity" tab proves it
by re-computing the Excel outputs to the nearest tenge.
Source data: Kaspi.kz Form 20-F for FY2025 (all amounts in KZT million).
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

st.set_page_config(page_title="Kaspi.kz Growth & Scenario Simulator", layout="wide")

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Inter Tight", "DejaVu Sans", "sans-serif"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700&display=swap');
html, body, .stApp, .stMarkdown, .stMetric, p, h1, h2, h3, h4, label, input, button, textarea, td, th {
    font-family: 'Inter Tight', sans-serif;
}
/* Top bar: take it out of the document flow so it no longer reserves empty space */
header[data-testid="stHeader"], .stAppHeader {
    position: absolute !important; top: 0 !important; right: 0 !important;
    background: transparent !important; z-index: 99999 !important;
}
.block-container { padding-top: 2rem !important; }

/* Sidebar: collapse the empty header block (the div that was 60px tall) and keep only the « arrow */
[data-testid="stSidebarHeader"] {
    height: 0 !important; min-height: 0 !important; padding: 0 !important; margin: 0 !important;
    overflow: visible !important;
}
[data-testid="stSidebarCollapseButton"] {
    position: absolute !important; top: 0.6rem !important; right: 0.6rem !important; z-index: 10;
}
[data-testid="stSidebarUserContent"] { padding-top: 0.75rem !important; }
[data-testid="stSidebarUserContent"] h2:first-of-type { margin-top: 0 !important; padding-top: 0 !important; }
.hero-section { margin-bottom: 24px; }
.hero-title { font-size: 38px; font-weight: 600; line-height: 1.15; margin-bottom: 0.8rem; }
.hero-desc { font-size: 17px; opacity: 0.75; line-height: 1.5; max-width: 940px; }
.chart-title { font-size: 19px; font-weight: 600; margin-bottom: 8px; }
hr { margin-top: 8px !important; margin-bottom: 8px !important; }
@media (max-width: 1400px) { [data-testid="stMetricValue"] { font-size: 24px !important; } }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 2025 base data (20-F, KZT million) - same inputs as Excel Raw_Data
# ----------------------------------------------------------------------------
TPV_25 = 44_219_000          # Payments TPV
PAY_INTEREST_25 = 147_963    # Payments interest revenue
GMV_3P_25 = 6_423_000        # Marketplace 3P GMV (KZ)
MKT_OTHER_25 = 228_532       # KZ 1P retail + interest + other gains
TFV_25 = 11_652_000          # Fintech total financing volume

# 2025 "replay" actuals on the model's basis (Excel column F)
REPLAY = {
    "rev_pay": 658_726, "rev_mkt": 899_880, "rev_fin": 1_561_874,   # fintech excl. other losses
    "ni_pay": 433_001, "ni_mkt": 372_791, "ni_fin": 354_933,
    "fin_other": -18_940,
}
REPLAY["rev"] = REPLAY["rev_pay"] + REPLAY["rev_mkt"] + REPLAY["rev_fin"]      # 3,120,480
REPLAY["ni"] = REPLAY["ni_pay"] + REPLAY["ni_mkt"] + REPLAY["ni_fin"]          # 1,160,725

# ----------------------------------------------------------------------------
# Drivers: key -> (label, min, max, step, format, group)   [all in % unless noted]
# ----------------------------------------------------------------------------
DRIVERS = {
    "tpv_g":   ("TPV growth, %", 0.0, 30.0, 0.5, "%.1f", "1. Payments"),
    "pay_tr":  ("Payments fee take rate, %", 0.90, 1.40, 0.005, "%.3f", "1. Payments"),
    "pay_ig":  ("Payments interest revenue growth, %", -20.0, 25.0, 1.0, "%.0f", "1. Payments"),
    "gmv_g":   ("3P GMV growth, %", 0.0, 25.0, 0.5, "%.1f", "2. Marketplace"),
    "mkt_tr":  ("Marketplace take rate (fee / 3P GMV), %", 9.5, 12.5, 0.05, "%.2f", "2. Marketplace"),
    "oth_g":   ("Other marketplace revenue growth (1P etc.), %", 0.0, 50.0, 1.0, "%.0f", "2. Marketplace"),
    "tfv_g":   ("Loan origination (TFV) growth, %", 0.0, 30.0, 0.5, "%.1f", "3. Fintech"),
    "conv":    ("TFV-to-portfolio conversion (x)", 1.50, 2.20, 0.01, "%.2f", "3. Fintech"),
    "yld":     ("Fintech yield on avg net loan portfolio, %", 20.0, 27.0, 0.1, "%.1f", "3. Fintech"),
    "prov":    ("Provision / avg net loan portfolio, %", 1.0, 7.0, 0.1, "%.1f", "3. Fintech"),
    "m_pay":   ("Payments net margin, %", 50.0, 75.0, 0.1, "%.1f", "4. Cost layer"),
    "m_mkt":   ("Marketplace (KZ) net margin, %", 25.0, 55.0, 0.1, "%.1f", "4. Cost layer"),
    # ИСПРАВЛЕНИЕ ЗДЕСЬ: расширили границы для ie (от 8.0) и opex (до 25.0)
    "ie":      ("Fintech interest expense / avg net portfolio, %", 8.0, 18.0, 0.1, "%.1f", "4. Cost layer"),
    "opex":    ("Fintech opex & tax, % of gross revenue", 4.0, 25.0, 0.1, "%.1f", "4. Cost layer"),
}
ORDER = list(DRIVERS.keys())

# Scenario presets = Excel Analysis C67:E91 (percent units)
PRESETS = {
    "Bear Case": dict(tpv_g=10, pay_tr=1.10, pay_ig=-10, gmv_g=6, mkt_tr=10.45, oth_g=10, tfv_g=5,
                      conv=1.85, yld=23.0, prov=4.9, m_pay=60.0, m_mkt=36.0, ie=13.8, opex=19.0),
    "Base Case": dict(tpv_g=15, pay_tr=1.13, pay_ig=8, gmv_g=10, mkt_tr=10.90, oth_g=25, tfv_g=13,
                      conv=1.80, yld=24.0, prov=2.4, m_pay=65.7, m_mkt=41.4, ie=11.9, opex=17.5),
    "Bull Case": dict(tpv_g=20, pay_tr=1.155, pay_ig=12, gmv_g=14, mkt_tr=11.20, oth_g=35, tfv_g=18,
                      conv=1.75, yld=24.5, prov=1.9, m_pay=68.0, m_mkt=45.0, ie=9.8, opex=16.5),
}
# 2025 anchors shown next to the sliders (history the assumptions are tied to)
ANCHORS = {
    "tpv_g": "2025 actual: +18.8%", "pay_tr": "2024: 1.233% -> 2025: 1.155%", "pay_ig": "2025 actual: +15.5%",
    "gmv_g": "2024: +41.9%, 2025: +10.8%", "mkt_tr": "2024: 9.70% -> 2025: 10.45%",
    "oth_g": "2025 actual: +33.9%", "tfv_g": "2025 actual: +13.1%", "conv": "2024: 2.11 -> 2025: 1.82",
    "yld": "2024: 25.98% -> 2025: 24.35%", "prov": "2025: 2.52% (20-F Cost of Risk 2.2% is on gross portfolio)",
    "m_pay": "2025: 65.7%", "m_mkt": "2025: 41.4% (KZ, ex-Hepsiburada loss)",
    "ie": "2025: 14.2%", "opex": "2025: 7.5%",
}


def project(p, fin_other=0.0, tpv_g_pct=None):
    """2026E projection. p holds percent-unit drivers; formulas mirror Excel rows 78-98."""
    tpv_g, pay_tr, pay_ig = p["tpv_g"] / 100, p["pay_tr"] / 100, p["pay_ig"] / 100
    gmv_g, mkt_tr, oth_g = p["gmv_g"] / 100, p["mkt_tr"] / 100, p["oth_g"] / 100
    tfv_g, conv, yld = p["tfv_g"] / 100, p["conv"], p["yld"] / 100
    prov, m_pay, m_mkt = p["prov"] / 100, p["m_pay"] / 100, p["m_mkt"] / 100
    ie, opex = p["ie"] / 100, p["opex"] / 100

    rev_pay = TPV_25 * (1 + tpv_g) * pay_tr + PAY_INTEREST_25 * (1 + pay_ig)
    rev_mkt = GMV_3P_25 * (1 + gmv_g) * mkt_tr + MKT_OTHER_25 * (1 + oth_g)
    portfolio = TFV_25 * (1 + tfv_g) / conv
    rev_fin = portfolio * yld
    cost_risk = portfolio * prov
    int_exp = portfolio * ie
    opex_tax = rev_fin * opex
    ni_pay = rev_pay * m_pay
    ni_mkt = rev_mkt * m_mkt
    ni_fin = rev_fin - cost_risk - int_exp - opex_tax + fin_other
    rev = rev_pay + rev_mkt + rev_fin
    ni = ni_pay + ni_mkt + ni_fin
    return dict(rev_pay=rev_pay, rev_mkt=rev_mkt, rev_fin=rev_fin, rev=rev,
                ni_pay=ni_pay, ni_mkt=ni_mkt, ni_fin=ni_fin, ni=ni,
                portfolio=portfolio, cost_risk=cost_risk, int_exp=int_exp, opex_tax=opex_tax,
                margin=ni / rev)


# Excel "2025 replay" inputs (column F): zero growth, 2025 actual ratios
REPLAY_PARAMS = dict(
    tpv_g=0, pay_tr=510_763 / TPV_25 * 100, pay_ig=0, gmv_g=0, mkt_tr=671_348 / GMV_3P_25 * 100, oth_g=0,
    tfv_g=0, conv=TFV_25 / 6_415_000, yld=1_561_874 / 6_415_000 * 100, prov=150_798 / 6_415_000 * 100,
    m_pay=433_001 / 658_726 * 100, m_mkt=(279_773 + 93_018) / 899_880 * 100,
    ie=763_964 / 6_415_000 * 100,
    opex=(1_561_874 - 18_940 - 763_964 - 150_798 - 354_933) / 1_561_874 * 100,
)

# Snapshot of the Excel outputs (Analysis!C83:E83, C98:E98, F83, F98) for the integrity check
EXCEL_SNAPSHOT = {
    "Bear Case": {"rev": 3_152_135.888378, "ni": 742_930.579492},
    "Base Case": {"rev": 3_545_776.645000, "ni": 1_321_929.550332},
    "Bull Case": {"rev": 3_832_111.140000, "ni": 1_725_374.188286},
    "2025 replay": {"rev": 3_120_480.0, "ni": 1_160_725.0},
}


# ----------------------------------------------------------------------------
# Session state & scenario handling
# ----------------------------------------------------------------------------
def apply_preset(name):
    for k, v in PRESETS[name].items():
        st.session_state[f"d_{k}"] = float(v)


def on_scenario_change():
    apply_preset(st.session_state.scenario_selector)


if "d_tpv_g" not in st.session_state:
    apply_preset("Base Case")

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown("""
<div class="hero-section">
  <div class="hero-title">Kaspi.kz: Growth Consulting & Unit Economics Simulator</div>
  <div class="hero-desc">
    A 2026E scenario model for Kaspi's Kazakhstan ecosystem built on the FY2025 Form 20-F. It projects
    <b>revenue and net income</b> for Payments, Marketplace and Fintech from 14 drivers, and is
    reconciled line-by-line to the accompanying Excel model (see the <i>Model Integrity</i> tab).
  </div>
</div>
""", unsafe_allow_html=True)
st.caption(
    "Independent project based on public filings (Kaspi.kz Form 20-F FY2025). "
    "Not affiliated with Kaspi.kz. Not investment advice."
)

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
st.sidebar.header("🎛️ Scenario & Drivers (2026E)")
st.sidebar.selectbox("📊 Scenario preset", list(PRESETS.keys()), index=1,
                     key="scenario_selector", on_change=on_scenario_change)
st.sidebar.button("↺ Reset sliders to selected preset", on_click=on_scenario_change, use_container_width=True)

params = {}
groups = {}
for k in ORDER:
    groups.setdefault(DRIVERS[k][5], []).append(k)
for g, keys in groups.items():
    with st.sidebar.expander(g, expanded=g.startswith(("1", "2", "3"))):
        for k in keys:
            label, lo, hi, step, fmt, _ = DRIVERS[k]
            params[k] = st.slider(label, lo, hi, step=step, format=fmt, key=f"d_{k}", help=ANCHORS[k])

active = next((n for n, pv in PRESETS.items()
               if all(abs(params[k] - pv[k]) < 1e-9 for k in ORDER)), None)
active_label = active if active else "Custom (manual override)"

res = project(params)
base_res = REPLAY  # 2025 replay basis

# ----------------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------------
tab_sim, tab_check, tab_method = st.tabs(["📊 Simulator", "✅ Model Integrity (vs Excel)", "📘 Methodology & Limitations"])

with tab_sim:
    st.caption(f"Active scenario: **{active_label}**  ·  KZ standalone (excludes Türkiye)  ·  KZT million")

    yoy_rev = res["rev"] / base_res["rev"] - 1
    yoy_ni = res["ni"] / base_res["ni"] - 1
    margin_25 = base_res["ni"] / base_res["rev"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total KZ revenue", f"₸ {res['rev']:,.0f}M", f"{yoy_rev*100:+.1f}% vs 2025")
    c2.metric("Total KZ net income", f"₸ {res['ni']:,.0f}M", f"{yoy_ni*100:+.1f}% vs 2025")
    c3.metric("Net margin", f"{res['margin']*100:.1f}%", f"{(res['margin']-margin_25)*100:+.1f} pp vs 2025")
    c4.metric("Fintech share of net income", f"{res['ni_fin']/res['ni']*100:.1f}%",
              f"{res['rev_fin']/res['rev']*100:.1f}% of revenue", delta_color="off")

    st.divider()
    left, right = st.columns(2)
    # Theme-aware chart palette: opaque background that matches the active Streamlit theme,
    # so axis text stays readable in both light and dark mode.
    try:
        theme_type = st.context.theme.type  # "light" / "dark" (Streamlit >= 1.46)
    except Exception:
        theme_type = None
    if theme_type == "dark":
        bg, txt, axis_c, ref_c = "#0e1117", "#e2e8f0", "#475569", "#94a3b8"
    else:  # light theme, or unknown -> white card with dark text (readable everywhere)
        bg, txt, axis_c, ref_c = "#ffffff", "#1e293b", "#94a3b8", "#64748b"

    def style(ax, fig, ylabel):
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        ax.set_ylabel(ylabel, color=txt)
        ax.tick_params(colors=txt)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1000:,.0f}"))  # KZT mn -> KZT bn, no "1e6"
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(axis_c)
        ax.grid(axis="x", visible=False)

    with left:
        st.markdown('<div class="chart-title">2026E revenue vs net income by segment</div>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(6, 4))
        segs = ["Payments", "Marketplace (KZ)", "Fintech"]
        rv = [res["rev_pay"], res["rev_mkt"], res["rev_fin"]]
        nv = [res["ni_pay"], res["ni_mkt"], res["ni_fin"]]
        x = range(3)
        w = 0.38
        ax.bar([i - w / 2 for i in x], rv, w, label="Revenue", color="#64748b")
        ax.bar([i + w / 2 for i in x], nv, w, label="Net income", color="#E31937")
        top = max(rv + nv)
        for i in x:
            ax.text(i - w / 2, rv[i] + top * 0.02, f"{rv[i]/1000:,.0f}", ha="center", fontsize=8, color=txt)
            ax.text(i + w / 2, max(nv[i], 0) + top * 0.02, f"{nv[i]/1000:,.0f}", ha="center", fontsize=8, color=txt)
        ax.set_xticks(list(x))
        ax.set_xticklabels(segs)
        ax.set_ylim(min(0, min(nv) * 1.3), top * 1.18)
        ax.axhline(0, color=axis_c, lw=0.8)
        style(ax, fig, "KZT bn")
        ax.legend(frameon=False, labelcolor=txt, fontsize=9)
        st.pyplot(fig)

    with right:
        st.markdown('<div class="chart-title">Bear / Base / Bull on the same engine</div>', unsafe_allow_html=True)
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        names = list(PRESETS.keys())
        pr = [project(PRESETS[n]) for n in names]
        revs = [r["rev"] for r in pr]
        nis = [r["ni"] for r in pr]
        x = range(3)
        ax2.bar([i - w / 2 for i in x], revs, w, label="Revenue", color="#64748b")
        ax2.bar([i + w / 2 for i in x], nis, w, label="Net income", color="#E31937")
        top2 = max(revs)
        for i in x:
            ax2.text(i - w / 2, revs[i] + top2 * 0.02, f"{revs[i]/1000:,.0f}", ha="center", fontsize=8, color=txt)
            ax2.text(i + w / 2, nis[i] + top2 * 0.02, f"{nis[i]/1000:,.0f}", ha="center", fontsize=8, color=txt)
        ax2.axhline(base_res["rev"], color=ref_c, ls="--", lw=1.0, label="2025 revenue")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels([n.replace(" Case", "") for n in names])
        ax2.set_ylim(0, top2 * 1.18)  # zero-based on purpose
        style(ax2, fig2, "KZT bn")
        ax2.legend(frameon=False, labelcolor=txt, fontsize=9, loc="upper left")
        st.pyplot(fig2)

    st.divider()
    st.subheader("Segment detail")
    seg_df = pd.DataFrame({
        "Segment": ["Payments", "Marketplace (KZ)", "Fintech", "Total"],
        "Revenue 2025": [REPLAY["rev_pay"], REPLAY["rev_mkt"], REPLAY["rev_fin"], REPLAY["rev"]],
        "Revenue 2026E": [res["rev_pay"], res["rev_mkt"], res["rev_fin"], res["rev"]],
        "Net income 2025": [REPLAY["ni_pay"], REPLAY["ni_mkt"], REPLAY["ni_fin"], REPLAY["ni"]],
        "Net income 2026E": [res["ni_pay"], res["ni_mkt"], res["ni_fin"], res["ni"]],
    })
    seg_df["Revenue YoY"] = seg_df["Revenue 2026E"] / seg_df["Revenue 2025"] - 1
    seg_df["NI YoY"] = seg_df["Net income 2026E"] / seg_df["Net income 2025"] - 1
    seg_df["NI margin 2026E"] = seg_df["Net income 2026E"] / seg_df["Revenue 2026E"]
    st.dataframe(
        seg_df.style.format({
            "Revenue 2025": "{:,.0f}", "Revenue 2026E": "{:,.0f}", "Net income 2025": "{:,.0f}",
            "Net income 2026E": "{:,.0f}", "Revenue YoY": "{:+.1%}", "NI YoY": "{:+.1%}", "NI margin 2026E": "{:.1%}",
        }),
        hide_index=True, use_container_width=True,
    )
    st.caption("2025 column = model-basis replay (Fintech revenue excludes ₸18.9bn other losses, which are not forecast). "
               "Segment net income is the 20-F segment figure; Marketplace is shown ex-Hepsiburada loss.")

    st.subheader("💡 Insights (computed from the current scenario)")
    shares_ni = {"Payments": res["ni_pay"] / res["ni"], "Marketplace": res["ni_mkt"] / res["ni"], "Fintech": res["ni_fin"] / res["ni"]}
    top_seg = max(shares_ni, key=shares_ni.get)
    fin_cost_ratio = (res["cost_risk"] + res["int_exp"] + res["opex_tax"]) / res["rev_fin"]
    st.info(
        f"* **Scenario:** {active_label}. Revenue ₸{res['rev']:,.0f}M ({yoy_rev*100:+.1f}% vs 2025 replay basis), "
        f"net income ₸{res['ni']:,.0f}M ({yoy_ni*100:+.1f}%), net margin {res['margin']*100:.1f}% vs {margin_25*100:.1f}% in 2025.\n"
        f"* **Profit mix:** {top_seg} is the largest contributor to net income ({shares_ni[top_seg]*100:.1f}%). "
        f"Fintech is {res['rev_fin']/res['rev']*100:.1f}% of revenue but {shares_ni['Fintech']*100:.1f}% of net income, "
        f"because funding, provisions and opex absorb {fin_cost_ratio*100:.0f}% of its gross revenue.\n"
        f"* **Fintech economics:** projected average net loan portfolio ₸{res['portfolio']/1e6:,.2f}T; "
        f"fintech net income ₸{res['ni_fin']:,.0f}M."
    )

with tab_check:
    st.markdown("This tab re-computes the Excel outputs with the app's engine. Differences should be **₸0.0**.")
    rows = []
    for name, pv in {**PRESETS, "2025 replay": REPLAY_PARAMS}.items():
        r = project(pv, fin_other=REPLAY["fin_other"] if name == "2025 replay" else 0.0)
        ex = EXCEL_SNAPSHOT[name]
        rows.append({"Case": name, "App revenue": r["rev"], "Excel revenue": ex["rev"], "Δ revenue": r["rev"] - ex["rev"],
                     "App net income": r["ni"], "Excel net income": ex["ni"], "Δ net income": r["ni"] - ex["ni"]})
    chk = pd.DataFrame(rows)
    st.dataframe(chk.style.format({c: "{:,.1f}" for c in chk.columns if c != "Case"}),
                 hide_index=True, use_container_width=True)
    if max(chk["Δ revenue"].abs().max(), chk["Δ net income"].abs().max()) < 1.0:
        st.success("All cases reconcile to Excel within ₸1 million.")
    else:
        st.error("The app no longer matches the Excel model - update one of them.")
    st.caption("Excel references: Analysis!C83:E83 (revenue), C98:E98 (net income), F83/F98 (2025 replay).")

with tab_method:
    st.markdown("""
### How the model works
| Segment | Revenue driver (2026E) | Net income |
|---|---|---|
| Payments | TPV × (1+g) × **fee** take rate + interest revenue × (1+g) | revenue × net margin |
| Marketplace (KZ) | **3P GMV** × (1+g) × **take rate (fee ÷ 3P GMV)** + other revenue (1P retail, interest, gains) × (1+g) | revenue × net margin |
| Fintech | TFV × (1+g) ÷ conversion = avg net loan portfolio; × yield | revenue − provisions − interest expense − opex & tax |

**Definitions corrected vs. earlier versions:** marketplace "take rate" is fee revenue ÷ 3P GMV (10.45% in 2025), not total
segment revenue ÷ GMV (13.5%, which includes 1P retail); Fintech yield is revenue ÷ average net loan portfolio, not ÷ TFV
(which is a flow of originations); Hepsiburada (₸1,031,592M) is fully removed from the KZ base.
""")
    with st.expander("⚠️ Known limitations & model caveats", expanded=True):
        st.markdown("""
- **Bear case is mostly a volume shock.** Roughly 57% of the Bear-vs-Base fall in Fintech net income comes from lower portfolio and yield, ~36% from provisions, ~7% from funding/opex. It is not a pure credit stress.
- **Margins are held as % of revenue.** Base keeps Marketplace net margin at 41.4% although 1P retail (lower margin) grows faster than fee revenue.
- **Interest expense is pegged to the loan portfolio.** Structurally it depends on the deposit base (Average Savings) and deposit rates.
- **Payments interest revenue is not linked to central-bank rates**; it is a plain growth input.
- **Standalone KZ.** Excludes Türkiye (Hepsiburada; 2025 net loss ₸89.6bn), so it is not a group forecast.
- **Fintech other gains/losses** are not forecast (set to 0), and segment net income includes allocated tax as reported in the 20-F.
- **Baseline.** YoY compares with the model-basis 2025 replay (₸3,120,480M revenue), which adds back ₸18.9bn Fintech other losses versus the reported KZ segment sum (₸3,101,540M).
- **Illustrative scenarios.** Driver values are analyst assumptions anchored to 2024-2025 history (hover over a slider), not company guidance.
""")
