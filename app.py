import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Page Configuration
st.set_page_config(
    page_title="Kaspi.kz Growth & Scenario Simulator",
    page_icon="📈",
    layout="wide"
)

# Принудительно устанавливаем шрифт Inter Tight для всех графиков Matplotlib
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Inter Tight', 'sans-serif']

# CSS для шрифта Inter Tight, хэдера, шапки, адаптивных метрик и отступов hr по 8px
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap');

        /* Принудительно применяем Inter Tight ко всему проекту */
        * {
            font-family: 'Inter Tight', sans-serif !important;
        }

        /* Выдергиваем хэдер из потока документов и прижимаем наверх */
        header.stAppHeader, .stAppHeader {
            position: absolute !important;
            top: 0px !important;
            right: 0px !important;
            background: transparent !important;
            z-index: 99999 !important;
        }
        
        /* Убираем лишнюю высоту и пространство верхней панели */
        .st-emotion-cache-10p9htt {
            height: auto !important;
            min-height: 0px !important;
            margin-bottom: -1rem !important;
        }
        
        /* Убираем лишний отступ у главного контейнера */
        .block-container {
            padding-top: 3rem !important;
        }

        /* Блок для заголовка и описания */
        .hero-section {
            margin-bottom: 32px !important;
        }
        
        .hero-title {
            font-size: 40px !important;
            font-weight: 600 !important;
            max-width: 1400px !important;
            line-height: 1.15 !important;
            color: #ffffff !important;
            margin-bottom: 1rem !important;
        }

        .hero-desc {
            font-size: 18px !important;
            color: #94a3b8 !important;
            line-height: 1.5 !important;
            max-width: 920px !important;
        }

        /* Компактный кастомный стиль для заголовков графиков */
        .chart-title {
            font-size: 20px !important;
            font-weight: 600 !important;
            color: #ffffff !important;
            margin-bottom: 10px !important;
        }

        /* Устанавливаем отступы для всех разделителей <hr> ровно по 8px сверху и снизу */
        hr {
            margin-top: 8px !important;
            margin-bottom: 8px !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
        }

        /* Настройка отступов в сайдбаре (меню) в 24px между элементами */
        section[data-testid="stSidebar"] .block-container > div {
            gap: 24px !important;
        }
        
        section[data-testid="stSidebar"] .stSubheader {
            margin-top: 12px !important;
            margin-bottom: 4px !important;
        }

        /* Адаптивность для метрик на экранах меньше 1400px */
        @media (max-width: 1400px) {
            [data-testid="stMetricValue"] {
                font-size: 24px !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# App Title & Overview wrapped in a single clean div container
st.markdown("""
    <div class="hero-section">
        <div class="hero-title">Kaspi.kz: Growth Consulting & Unit Economics Simulator</div>
        <div class="hero-desc">
            This interactive simulation tool is built upon official data from the SEC Form 20-F filings and interim financial results. 
            Adjust the core <b>Growth Levers</b> on the sidebar to dynamically stress-test ecosystem resilience and projected revenues.
        </div>
    </div>
""", unsafe_allow_html=True)

# Sidebar with Growth Levers & Scenario Presets
st.sidebar.header("🎛️ Growth Levers Control Panel (2026E)")

# Инициализация session_state для значений по умолчанию (Base Case)
if 'tpv' not in st.session_state:
    st.session_state.tpv = 15.0
if 'pay_tr' not in st.session_state:
    st.session_state.pay_tr = 1.49
if 'gmv' not in st.session_state:
    st.session_state.gmv = 12.0
if 'mkt_mon' not in st.session_state:
    st.session_state.mkt_mon = 14.1
if 'tfv' not in st.session_state:
    st.session_state.tfv = 13.0
if 'tfv_yield' not in st.session_state:
    st.session_state.tfv_yield = 13.2

# Эталонные значения пресетов
base_vals = (15.0, 1.49, 12.0, 14.1, 13.0, 13.2)
bear_vals = (10.0, 1.35, 8.0, 13.0, 8.0, 12.0)
bull_vals = (25.0, 1.65, 22.0, 15.5, 20.0, 14.5)

# Определяем текущий активный сценарий на основе ползунков
current_vals = (st.session_state.tpv, st.session_state.pay_tr, st.session_state.gmv, 
                st.session_state.mkt_mon, st.session_state.tfv, st.session_state.tfv_yield)

if current_vals == bear_vals:
    active_scenario = "Bear Case (Conservative)"
elif current_vals == bull_vals:
    active_scenario = "Bull Case (Aggressive)"
elif current_vals == base_vals:
    active_scenario = "Base Case"
else:
    active_scenario = "Custom (Manual Override)"

# Функция обработки выбора пресета
def apply_scenario():
    sel = st.session_state.scenario_selector
    if sel == "Bear Case (Conservative)":
        st.session_state.tpv = 10.0
        st.session_state.pay_tr = 1.35
        st.session_state.gmv = 8.0
        st.session_state.mkt_mon = 13.0
        st.session_state.tfv = 8.0
        st.session_state.tfv_yield = 12.0
    elif sel == "Bull Case (Aggressive)":
        st.session_state.tpv = 25.0
        st.session_state.pay_tr = 1.65
        st.session_state.gmv = 22.0
        st.session_state.mkt_mon = 15.5
        st.session_state.tfv = 20.0
        st.session_state.tfv_yield = 14.5
    elif sel == "Base Case":
        st.session_state.tpv = 15.0
        st.session_state.pay_tr = 1.49
        st.session_state.gmv = 12.0
        st.session_state.mkt_mon = 14.1
        st.session_state.tfv = 13.0
        st.session_state.tfv_yield = 13.2

# Всегда полный список опций в селекторе
scenario_options = [
    "Base Case", 
    "Bear Case (Conservative)", 
    "Bull Case (Aggressive)", 
    "Custom (Manual Override)"
]

# Синхронизируем индекс селектора с текущим активным сценарием
try:
    default_index = scenario_options.index(active_scenario)
except ValueError:
    default_index = 0

scenario = st.sidebar.selectbox(
    "📊 Macro Scenario Presets", 
    scenario_options,
    index=default_index,
    key="scenario_selector",
    on_change=apply_scenario
)

st.sidebar.divider()

st.sidebar.subheader("1. Payments Platform")
tpv_growth = st.sidebar.slider("TPV Growth (KZ), %", 5.0, 30.0, key='tpv', step=0.5) / 100
pay_take_rate = st.sidebar.slider("Payments Take Rate, %", 1.0, 2.0, key='pay_tr', step=0.01) / 100

st.sidebar.subheader("2. Marketplace Platform")
gmv_growth = st.sidebar.slider("GMV Growth (KZ), %", 5.0, 30.0, key='gmv', step=0.5) / 100
mkt_mon = st.sidebar.slider("Marketplace Monetization (Take Rate), %", 10.0, 20.0, key='mkt_mon', step=0.1) / 100

st.sidebar.subheader("3. Fintech Platform")
tfv_growth = st.sidebar.slider("Loan Origination (TFV) Growth, %", 5.0, 30.0, key='tfv', step=0.5) / 100
tfv_yield = st.sidebar.slider("Portfolio Yield (TFV Yield), %", 10.0, 20.0, key='tfv_yield', step=0.1) / 100

# Base Financials 2025 (KZ Standalone from Raw_Data)
base_tpv = 44219000  # million KZT
base_gmv = 6657000   # million KZT
base_tfv = 11652000  # million KZT

# 2026E Revenue Projections Calculation
rev_payments = base_tpv * (1 + tpv_growth) * pay_take_rate
rev_marketplace = base_gmv * (1 + gmv_growth) * mkt_mon
rev_fintech = base_tfv * (1 + tfv_growth) * tfv_yield
total_kz_revenue = rev_payments + rev_marketplace + rev_fintech

# Main Screen KPI Metrics Display
st.subheader("📊 2026E Ecosystem Revenue Projections (KZ Standalone)")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Payments Revenue", f"₸ {rev_payments:,.0f}M", f"{tpv_growth*100:.1f}% TPV growth")
col2.metric("Marketplace Revenue", f"₸ {rev_marketplace:,.0f}M", f"{mkt_mon*100:.1f}% Take Rate")
col3.metric("Fintech Revenue", f"₸ {rev_fintech:,.0f}M", f"{tfv_yield*100:.1f}% Yield")
col4.metric("Total KZ Revenue", f"₸ {total_kz_revenue:,.0f}M", "2026E Projections")

st.divider()

# Visualization Layout (Charts)
col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<div class="chart-title">💡 2026E Revenue Breakdown by Segment</div>', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    segments = ['Payments', 'Marketplace', 'Fintech']
    revenues = [rev_payments, rev_marketplace, rev_fintech]
    colors = ['#f59e0b', '#3b82f6', '#ef4444']
    
    ax.bar(segments, revenues, color=colors, width=0.5)
    ax.set_ylabel("Million KZT")
    ax.set_ylim(0, max(revenues) * 1.25)
    ax.grid(axis='x', visible=False)
    for i, v in enumerate(revenues):
        ax.text(i, v + (max(revenues) * 0.03), f"₸{v:,.0f}M", ha='center', weight='bold', fontsize=9)
    st.pyplot(fig)

with col_right:
    st.markdown('<div class="chart-title">⚖️ Comparison vs. Baseline Year (2025)</div>', unsafe_allow_html=True)
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    years = ['2025 (Actual)', '2026E (Simulator)']
    fact_2025 = 658726 + 936118 + 1542934  # Payments + KZ Marketplace + Fintech actuals
    totals = [fact_2025, total_kz_revenue]
    
    ax2.bar(years, totals, color=['#333333', '#E31937'], width=0.5)
    ax2.set_ylabel("Million KZT")
    ax2.set_ylim(0, max(totals) * 1.25)
    ax2.grid(axis='x', visible=False)
    for i, v in enumerate(totals):
        ax2.text(i, v + (max(totals) * 0.03), f"₸{v:,.0f}M", ha='center', weight='bold', fontsize=9)
    st.pyplot(fig2)

st.divider()

# Динамический блок Executive Summary & Strategic Takeaways
st.subheader("💡 Executive Summary & Ecosystem Insights")

fintech_share = (rev_fintech / total_kz_revenue) * 100
yoy_growth = ((total_kz_revenue - fact_2025) / fact_2025) * 100

st.info(f"""
* **Macro Environment:** Currently simulating under **{active_scenario}**. Total projected standalone revenue reaches **₸ {total_kz_revenue:,.0f}M**, representing a **{yoy_growth:.1f}% YoY growth** compared to the 2025 baseline (~₸ 3.14T).
* **Monetization & Mix:** The Fintech segment acts as the primary profit engine, contributing **{fintech_share:.1f}%** of total ecosystem revenues. 
* **Strategic Takeaway:** Sensitivity analysis indicates that ecosystem resilience heavily relies on maintaining portfolio yield above 12% while scaling marketplace GMV velocity.
""")

st.divider()