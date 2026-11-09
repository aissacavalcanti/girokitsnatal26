"""
StockBridge · Giro de Estoque
=============================
giro = quantidade vendida ÷ (vendida + estoque atual)

Uso (somente neste PC):
  rodar_local.bat
  ou: python -m streamlit run app.py --server.address 127.0.0.1
"""
from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.giro import aggregate, build_base_giro, risk_flags, summarize
from src.loaders import load_classificacao_produtos, load_dcentro, load_estoque, load_vendas

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
EXEMPLO = DATA / "exemplo"
ULTIMA = DATA / "ultima"
PUBLICADA = DATA / "publicada"
META_ULTIMA = ULTIMA / "meta.json"
META_PUBLICADA = PUBLICADA / "meta.json"

# --- StockBridge palette (alto contraste) ---
SB = {
    "bg": "#0B1120",
    "bg_elevated": "#0F172A",
    "surface": "#1E293B",
    "surface_2": "#243447",
    "border": "#334155",
    "green": "#00E59A",
    "green_dim": "#00C887",
    "green_soft": "rgba(0, 229, 154, 0.14)",
    "blue": "#38BDF8",
    "blue_deep": "#3B82F6",
    "blue_soft": "rgba(56, 189, 248, 0.16)",
    "white": "#FFFFFF",
    "gray_1": "#F1F5F9",
    "gray_2": "#CBD5E1",
    "gray_3": "#94A3B8",
    "danger": "#FB7185",
    "warning": "#FBBF24",
}

# Só azul / verde / cinza / branco (sem rosa/roxo)
PLOTLY_COLORS = [
    "#00E59A",
    "#38BDF8",
    "#3B82F6",
    "#94A3B8",
    "#34D399",
    "#7DD3FC",
    "#64748B",
    "#A5B4FC",
]

st.set_page_config(
    page_title="StockBridge · Giro",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_theme() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
  font-family: Inter, system-ui, sans-serif;
}}

.stApp {{
  background: {SB["bg"]};
  color: {SB["gray_1"]};
}}

[data-testid="stSidebar"] {{
  background: {SB["bg_elevated"]};
  border-right: 1px solid {SB["border"]};
}}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stMarkdown {{
  color: {SB["gray_2"]} !important;
}}

.block-container {{
  padding-top: 1.4rem;
  padding-bottom: 3rem;
  max-width: 1400px;
}}

h1, h2, h3 {{
  color: {SB["white"]} !important;
  font-weight: 700 !important;
}}

/* Header */
.sb-brand {{
  color: {SB["white"]};
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 1rem;
}}

.sb-header {{
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 0.25rem;
}}

.sb-icon {{
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: {SB["blue_deep"]};
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 0 0 4px {SB["blue_soft"]};
}}

.sb-eyebrow {{
  color: {SB["green"]};
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 0.2rem 0;
}}

.sb-title {{
  font-size: 2.1rem;
  font-weight: 800;
  line-height: 1.1;
  margin: 0;
  color: {SB["white"]};
}}

.sb-title span {{
  color: {SB["green"]};
}}

.sb-tagline {{
  color: {SB["gray_2"]};
  font-size: 0.95rem;
  line-height: 1.45;
  margin: 0.55rem 0 1.5rem 0;
  max-width: 640px;
}}

.sb-kpi-row {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.75rem;
  margin: 0.5rem 0 1.75rem 0;
  padding: 1.25rem 0;
  border-top: 1px solid {SB["border"]};
  border-bottom: 1px solid {SB["border"]};
}}

.sb-kpi-row.sb-kpi-6 {{
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
}}

@media (max-width: 1200px) {{
  .sb-kpi-row.sb-kpi-6 {{
    grid-template-columns: repeat(3, 1fr);
  }}
}}

.sb-kpi-value {{
  color: {SB["green"]};
  font-size: 2.35rem;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
}}

.sb-kpi-row.sb-kpi-6 .sb-kpi-value {{
  font-size: clamp(1.2rem, 1.8vw, 1.85rem);
}}

.sb-kpi-value.sb-kpi-money {{
  font-size: clamp(1.35rem, 2.1vw, 2.1rem);
  white-space: nowrap;
}}

.sb-kpi-row.sb-kpi-6 .sb-kpi-value.sb-kpi-money {{
  font-size: clamp(1.05rem, 1.4vw, 1.45rem);
}}

.sb-kpi-label {{
  color: {SB["gray_2"]};
  font-size: 0.9rem;
  line-height: 1.4;
  margin-top: 0.35rem;
  max-width: 280px;
}}

.sb-formula {{
  background: {SB["green_soft"]};
  border: 1px solid rgba(0, 229, 154, 0.35);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  color: {SB["gray_1"]};
  font-size: 0.9rem;
  margin-bottom: 1.25rem;
}}

.sb-formula strong {{
  color: {SB["green"]};
}}

.sb-section-title {{
  color: {SB["white"]};
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0.5rem 0 0.75rem 0;
}}

.sb-chip {{
  display: inline-block;
  background: {SB["blue_soft"]};
  color: #BAE6FD;
  border-radius: 6px;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.35rem;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
  gap: 0.25rem;
  background: transparent;
  border-bottom: 1px solid {SB["border"]};
}}

.stTabs [data-baseweb="tab"] {{
  background: transparent;
  color: {SB["gray_3"]};
  border-radius: 8px 8px 0 0;
  padding: 0.65rem 1rem;
  font-weight: 600;
}}

.stTabs [aria-selected="true"] {{
  color: {SB["green"]} !important;
  background: {SB["green_soft"]} !important;
  border-bottom: 2px solid {SB["green"]} !important;
}}

.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{
  background: transparent !important;
  display: none;
}}

[data-testid="stMetricValue"] {{
  color: {SB["green"]} !important;
  font-weight: 800 !important;
}}

[data-testid="stMetricLabel"] {{
  color: {SB["gray_2"]} !important;
}}

.stSelectbox label, .stMultiSelect label, .stTextInput label, .stToggle label {{
  color: {SB["gray_2"]} !important;
}}

div[data-baseweb="select"] > div,
.stTextInput input {{
  background: {SB["surface"]} !important;
  border-color: {SB["border"]} !important;
  color: {SB["white"]} !important;
}}

/* Pills dos filtros: fundo escuro + texto claro (alto contraste) */
span[data-baseweb="tag"],
[data-baseweb="tag"] {{
  background-color: #0F3D2E !important;
  background-image: none !important;
  color: #ECFDF5 !important;
  border: 1px solid #2DD4A0 !important;
}}

span[data-baseweb="tag"] span,
[data-baseweb="tag"] span,
span[data-baseweb="tag"] p,
[data-baseweb="tag"] * {{
  color: #ECFDF5 !important;
}}

[data-baseweb="tag"] svg {{
  fill: #ECFDF5 !important;
}}

/* Fallback se o tema pintar o tag com primaryColor claro */
[data-baseweb="tag"][kind],
div[data-baseweb="select"] span[data-baseweb="tag"] {{
  background-color: #0F3D2E !important;
  color: #ECFDF5 !important;
}}

/* Não esconder o controle da sidebar (seta para reabrir) */
[data-testid="stSidebarCollapsedControl"] {{
  display: flex !important;
  visibility: visible !important;
  background: {SB["surface"]} !important;
  border: 1px solid {SB["border"]} !important;
  color: {SB["green"]} !important;
}}

[data-testid="stSidebarCollapsedControl"] svg {{
  fill: {SB["green"]} !important;
}}

/* Esconde só Deploy / toolbar, não a seta da sidebar */
[data-testid="stToolbar"] {{
  display: none !important;
}}

div[data-testid="stDecoration"] {{
  display: none !important;
}}

[data-baseweb="switch"] span[data-checked="true"],
button[role="switch"][aria-checked="true"] {{
  background-color: {SB["green"]} !important;
}}

/* Tabelas escuras (sem fundo branco) */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stTable"] {{
  background: {SB["surface"]} !important;
  border: 1px solid {SB["border"]} !important;
  border-radius: 10px !important;
  overflow: hidden;
}}

[data-testid="stDataFrame"] [role="grid"],
[data-testid="stDataFrame"] canvas,
div[data-testid="stDataFrame"] > div {{
  background-color: {SB["surface"]} !important;
}}

.stDownloadButton button, .stButton button {{
  background: {SB["surface_2"]} !important;
  color: {SB["white"]} !important;
  border: 1px solid {SB["border"]} !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}}

.stDownloadButton button:hover, .stButton button:hover {{
  border-color: {SB["green"]} !important;
  color: {SB["green"]} !important;
}}

hr {{
  border-color: {SB["border"]} !important;
}}

#MainMenu, footer {{
  visibility: hidden;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def plotly_layout(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=SB["gray_1"], size=12),
        title=dict(font=dict(color=SB["white"], size=15, family="Inter"), x=0, xanchor="left"),
        legend=dict(
            bgcolor="rgba(15,23,42,0.85)",
            bordercolor=SB["border"],
            borderwidth=1,
            font=dict(color=SB["gray_1"]),
        ),
        margin=dict(t=48, b=24, l=24, r=16),
        colorway=PLOTLY_COLORS,
        height=height,
    )
    fig.update_xaxes(
        gridcolor=SB["border"],
        zerolinecolor=SB["border"],
        linecolor=SB["border"],
        tickfont=dict(color=SB["gray_2"], size=11),
        title_font=dict(color=SB["gray_2"]),
    )
    fig.update_yaxes(
        gridcolor=SB["border"],
        zerolinecolor=SB["border"],
        linecolor=SB["border"],
        tickfont=dict(color=SB["gray_2"], size=11),
        title_font=dict(color=SB["gray_2"]),
    )
    return fig


def fmt_int(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def fmt_pct(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money_short(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"R$ {x / 1_000_000:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(x) >= 1_000:
        return f"R$ {x / 1_000:,.1f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    return fmt_money(x)


def render_header() -> None:
    st.markdown('<div class="sb-brand">Gentil Negócios</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="sb-header">
          <div class="sb-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M4 14c2.5-4 5.5-4 8-1s5.5 3 8-1" stroke="white" stroke-width="2.2" stroke-linecap="round"/>
              <path d="M4 10c2.5-4 5.5-4 8-1s5.5 3 8-1" stroke="white" stroke-width="2.2" stroke-linecap="round" opacity="0.55"/>
            </svg>
          </div>
          <div>
            <p class="sb-eyebrow">MVP · Inteligência de Estoque</p>
            <h1 class="sb-title">Stock<span>Bridge</span> · Giro</h1>
          </div>
        </div>
        <p class="sb-tagline">
          Análise de giro de kits, lançamentos e itens promocionados.
          Distribuição por loja e praça. Decisão baseada em dados.
        </p>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(stats: dict) -> None:
    st.markdown(
        f"""
        <div class="sb-kpi-row">
          <div>
            <div class="sb-kpi-value">{fmt_pct(stats["giro"])}</div>
            <div class="sb-kpi-label">giro geral — vendida ÷ (vendida + estoque atual)</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(stats["vendida"])}</div>
            <div class="sb-kpi-label">unidades vendidas · {fmt_int(stats["estoque"])} em estoque agora</div>
          </div>
          <div>
            <div class="sb-kpi-value sb-kpi-money">{fmt_money(stats["faturamento"])}</div>
            <div class="sb-kpi-label">faturamento · {stats["lojas"]} lojas · {stats["skus"]} SKUs · {stats["pracas"]} praças</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis_panorama(stats: dict, escopo: str) -> None:
    """Big numbers detalhados para o panorama de uma praça (ou todas)."""
    st.markdown(
        f"""
        <div class="sb-kpi-row sb-kpi-6">
          <div>
            <div class="sb-kpi-value">{fmt_pct(stats["giro"])}</div>
            <div class="sb-kpi-label">giro · {escopo}</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(stats["vendida"])}</div>
            <div class="sb-kpi-label">unidades vendidas</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(stats["estoque"])}</div>
            <div class="sb-kpi-label">estoque atual</div>
          </div>
          <div>
            <div class="sb-kpi-value sb-kpi-money">{fmt_money(stats["faturamento"])}</div>
            <div class="sb-kpi-label">faturamento</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(stats["lojas"])}</div>
            <div class="sb-kpi-label">lojas</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(stats["skus"])}</div>
            <div class="sb-kpi-label">kits / SKUs</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tab_resumo_praca(filtered: pd.DataFrame) -> None:
    """Panorama por praça: KPIs + detalhe por lojas e por kits."""
    st.markdown('<p class="sb-section-title">Resumo por praça</p>', unsafe_allow_html=True)
    st.caption("Filtre a praça para ver o panorama geral, com big numbers e ranking de lojas e kits.")

    pracas = sorted(filtered["praca"].dropna().unique().tolist())
    if not pracas:
        st.warning("Nenhuma praça disponível nos filtros atuais.")
        return

    c_filtro, c_info = st.columns([1.2, 2])
    with c_filtro:
        praca_sel = st.selectbox(
            "Praça",
            options=["Todas"] + pracas,
            index=0,
            key="resumo_praca_select",
        )
    with c_info:
        if praca_sel == "Todas":
            st.caption("Exibindo consolidado de todas as praças da base filtrada.")
        else:
            st.caption(f"Panorama exclusivo da praça **{praca_sel}**.")

    subset = filtered if praca_sel == "Todas" else filtered[filtered["praca"] == praca_sel]
    if subset.empty:
        st.warning("Sem dados para esta praça com os filtros atuais.")
        return

    stats = summarize(subset)
    escopo = "todas as praças" if praca_sel == "Todas" else praca_sel
    render_kpis_panorama(stats, escopo)

    # Participação vs rede (quando uma praça está selecionada)
    if praca_sel != "Todas":
        geral = summarize(filtered)
        part_venda = (stats["vendida"] / geral["vendida"]) if geral["vendida"] else 0
        part_fat = (stats["faturamento"] / geral["faturamento"]) if geral["faturamento"] else 0
        part_est = (stats["estoque"] / geral["estoque"]) if geral["estoque"] else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("% da rede em vendas", fmt_pct(part_venda))
        m2.metric("% da rede em faturamento", fmt_pct(part_fat))
        m3.metric("% da rede em estoque", fmt_pct(part_est))

    por_loja = aggregate(subset, ["bcps", "loja", "canal"]).sort_values("giro", ascending=False)
    por_kit = aggregate(subset, ["codigo", "descricao", "tipo"]).sort_values("giro", ascending=False)
    por_canal = aggregate(subset, ["canal"]).sort_values("giro", ascending=False)

    # Gráficos de apoio
    g1, g2 = st.columns(2)
    with g1:
        top_lojas = por_loja.head(12).sort_values("vendida", ascending=True)
        fig_l = px.bar(
            top_lojas,
            x="vendida",
            y="loja",
            orientation="h",
            title=f"Lojas — quantidade vendida (top {len(top_lojas)})",
            labels={"vendida": "Vendida", "loja": "Loja"},
            color_discrete_sequence=[SB["green"]],
        )
        st.plotly_chart(plotly_layout(fig_l, 380), use_container_width=True)
    with g2:
        top_kits = por_kit.head(12).sort_values("vendida", ascending=True)
        fig_k = px.bar(
            top_kits,
            x="vendida",
            y="descricao",
            orientation="h",
            title=f"Kits — quantidade vendida (top {len(top_kits)})",
            labels={"vendida": "Vendida", "descricao": "Kit"},
            color_discrete_sequence=[SB["blue"]],
        )
        st.plotly_chart(plotly_layout(fig_k, 380), use_container_width=True)

    if len(por_canal) > 0:
        fig_c = go.Figure()
        fig_c.add_bar(name="Vendida", x=por_canal["canal"], y=por_canal["vendida"], marker_color=SB["green"])
        fig_c.add_bar(name="Estoque", x=por_canal["canal"], y=por_canal["estoque"], marker_color=SB["blue"])
        fig_c.update_layout(barmode="group", title=f"Canal dentro de {escopo}", yaxis_title="Quantidade")
        st.plotly_chart(plotly_layout(fig_c, 300), use_container_width=True)

    t_lojas, t_kits = st.tabs(["Detalhe por lojas", "Detalhe por kits"])
    with t_lojas:
        st.caption(f"{len(por_loja)} lojas · ordenado por giro")
        show_table(
            por_loja[["bcps", "loja", "canal", "vendida", "estoque", "disponivel", "giro", "faturamento", "skus"]],
            money_cols=["faturamento"],
            pct_cols=["giro"],
            height=440,
        )
        st.download_button(
            "Baixar lojas da praça (.xlsx)",
            data=dataframe_export(por_loja),
            file_name=f"resumo_lojas_{praca_sel}.xlsx".replace(" ", "_"),
            key="dl_resumo_lojas",
        )
    with t_kits:
        st.caption(f"{len(por_kit)} kits · ordenado por giro")
        show_table(
            por_kit[["codigo", "descricao", "tipo", "vendida", "estoque", "disponivel", "giro", "faturamento", "lojas"]],
            money_cols=["faturamento"],
            pct_cols=["giro"],
            height=440,
        )
        st.download_button(
            "Baixar kits da praça (.xlsx)",
            data=dataframe_export(por_kit),
            file_name=f"resumo_kits_{praca_sel}.xlsx".replace(" ", "_"),
            key="dl_resumo_kits",
        )


def _load_defaults():
    """Sem cache — evita devolver DataFrame antigo sem coluna data."""
    vendas = load_vendas(EXEMPLO / "vendas_abc_kits.csv", tipo="kit")
    estoque = load_estoque(EXEMPLO / "saldo_estoque_kits.csv", tipo="kit")
    dcentro = load_dcentro(DATA / "dcentros.csv")
    return vendas, estoque, dcentro


def _write_upload(file_obj, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = file_obj.getvalue() if hasattr(file_obj, "getvalue") else file_obj.read()
    dest.write_bytes(raw)
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)


def ler_meta(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def ler_meta_ultima() -> dict:
    return ler_meta(META_ULTIMA)


def ultima_disponivel() -> bool:
    return (ULTIMA / "vendas.csv").exists() and (ULTIMA / "estoque.csv").exists()


def publicada_disponivel() -> bool:
    return (PUBLICADA / "vendas.csv").exists() and (PUBLICADA / "estoque.csv").exists()


def exigir_senha() -> bool:
    """Bloqueia o dash se APP_PASSWORD estiver em secrets (Streamlit Cloud / local)."""
    try:
        senha_ok = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        senha_ok = ""
    if not senha_ok:
        return True
    if st.session_state.get("autenticado"):
        return True

    st.markdown(
        f"""
        <div class="sb-header">
          <div>
            <div class="sb-kicker">ACESSO RESTRITO · GENTIL NEGÓCIOS</div>
            <h1 class="sb-title">StockBridge · Giro</h1>
            <p class="sb-sub">Digite a senha da equipe para abrir o painel.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")
    if entrar:
        if senha == senha_ok:
            st.session_state["autenticado"] = True
            st.rerun()
        st.error("Senha incorreta.")
    return False


def salvar_ultima(f_vendas, f_estoque, f_dcentro=None, f_class=None, tipo_default: str = "kit") -> dict:
    ULTIMA.mkdir(parents=True, exist_ok=True)
    _write_upload(f_vendas, ULTIMA / "vendas.csv")
    _write_upload(f_estoque, ULTIMA / "estoque.csv")

    tem_dcentro = (ULTIMA / "dcentro.csv").exists() or (ULTIMA / "dcentro.xlsx").exists()
    if f_dcentro is not None:
        for stale in ("dcentro.csv", "dcentro.xlsx"):
            path_stale = ULTIMA / stale
            if path_stale.exists():
                path_stale.unlink()
        name = str(getattr(f_dcentro, "name", "")).lower()
        dest = ULTIMA / ("dcentro.xlsx" if name.endswith((".xlsx", ".xlsm", ".xls")) else "dcentro.csv")
        _write_upload(f_dcentro, dest)
        tem_dcentro = True

    tem_class = (ULTIMA / "classificacao.csv").exists()
    if f_class is not None:
        _write_upload(f_class, ULTIMA / "classificacao.csv")
        tem_class = True

    meta = {
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "tipo_default": tipo_default,
        "tem_dcentro": tem_dcentro,
        "tem_classificacao": tem_class,
        "nome_vendas": str(getattr(f_vendas, "name", "vendas.csv")),
        "nome_estoque": str(getattr(f_estoque, "name", "estoque.csv")),
    }
    META_ULTIMA.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def carregar_pasta_bases(pasta: Path, tipo_default: str):
    vendas = load_vendas(pasta / "vendas.csv", tipo=tipo_default)
    estoque = load_estoque(pasta / "estoque.csv", tipo=tipo_default)

    if (pasta / "dcentro.xlsx").exists():
        dcentro = load_dcentro(pasta / "dcentro.xlsx")
    elif (pasta / "dcentro.csv").exists():
        dcentro = load_dcentro(pasta / "dcentro.csv")
    else:
        dcentro = load_dcentro(DATA / "dcentros.csv")

    classificacao = None
    if (pasta / "classificacao.csv").exists():
        classificacao = load_classificacao_produtos(pasta / "classificacao.csv")

    return vendas, estoque, dcentro, classificacao


def carregar_ultima(tipo_default: str):
    return carregar_pasta_bases(ULTIMA, tipo_default)


def carregar_publicada(tipo_default: str):
    return carregar_pasta_bases(PUBLICADA, tipo_default)


def formatar_data_meta(meta: dict) -> str:
    raw = meta.get("atualizado_em")
    if not raw:
        return "—"
    try:
        return datetime.fromisoformat(raw).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(raw)


def load_data_panel():
    """Upload / última salva / publicada / exemplo — persiste em data/ultima/."""
    st.markdown('<p class="sb-section-title">Carregar bases</p>', unsafe_allow_html=True)
    st.caption(
        "Ao enviar ABC + Saldo, a base fica salva neste PC. "
        "Para o dash compartilhado, rode preparar_publicacao.bat e faça push no GitHub."
    )

    meta = ler_meta_ultima()
    meta_pub = ler_meta(META_PUBLICADA)
    tem_ultima = ultima_disponivel()
    tem_publicada = publicada_disponivel()

    if tem_ultima:
        st.markdown(
            f'<span class="sb-chip">salva</span> '
            f'<span style="color:{SB["green"]}">Última atualização: {formatar_data_meta(meta)}</span>'
            f'<span style="color:{SB["gray_2"]}"> · {meta.get("nome_vendas", "vendas")} + {meta.get("nome_estoque", "estoque")}</span>',
            unsafe_allow_html=True,
        )
    elif tem_publicada:
        st.markdown(
            f'<span class="sb-chip">publicada</span> '
            f'<span style="color:{SB["green"]}">Snapshot compartilhado: {formatar_data_meta(meta_pub)}</span>',
            unsafe_allow_html=True,
        )

    tipo_opts = ["kit", "lancamento", "promocionado"]
    tipo_idx = tipo_opts.index(meta["tipo_default"]) if meta.get("tipo_default") in tipo_opts else 0
    tipo_default = st.selectbox(
        "Tipo padrão dos itens",
        options=tipo_opts,
        index=tipo_idx,
        key="tipo_default",
        help="Enquanto não houver CSV de classificação, todos os SKUs ficam neste tipo.",
    )

    st.markdown("**1. Envie arquivos para atualizar (fica salvo automaticamente)**")
    c1, c2, c3 = st.columns(3)
    with c1:
        f_vendas = st.file_uploader("ABC Vendas (.csv)", type=["csv"], key="up_vendas")
    with c2:
        f_estoque = st.file_uploader("Saldo estoque (.csv)", type=["csv"], key="up_estoque")
    with c3:
        f_dcentro = st.file_uploader(
            "dCentro (.csv / .xlsx) — opcional",
            type=["csv", "xlsx"],
            key="up_dcentro",
            help="Se não enviar, usa o dCentro da última atualização ou data/dcentros.csv",
        )

    f_class = st.file_uploader(
        "Classificação de produtos (opcional) — codigo;tipo",
        type=["csv"],
        key="up_class",
        help="tipos: kit, lancamento, promocionado",
    )

    tem_upload = bool(f_vendas and f_estoque)

    col_a, col_b = st.columns(2)
    with col_a:
        if tem_ultima or tem_publicada:
            forcar_exemplo = st.toggle(
                "Usar exemplo (ignora a base salva/publicada)",
                value=False,
                key="usar_exemplo",
            )
        else:
            forcar_exemplo = st.toggle(
                "Usar bases de exemplo",
                value=not tem_upload,
                key="usar_exemplo",
            )
    with col_b:
        if tem_ultima and st.button("Apagar última atualização salva", key="btn_apagar_ultima"):
            for path_file in ULTIMA.glob("*"):
                if path_file.is_file():
                    path_file.unlink()
            st.success("Base salva removida.")
            st.rerun()

    classificacao = None

    if tem_upload:
        meta = salvar_ultima(f_vendas, f_estoque, f_dcentro, f_class, tipo_default=tipo_default)
        vendas, estoque, dcentro, classificacao = carregar_ultima(tipo_default)
        st.markdown(
            f'<span class="sb-chip">upload</span> '
            f'<span style="color:{SB["green"]}">'
            f"Salvo em {formatar_data_meta(meta)} · {len(vendas):,} linhas de venda · {len(estoque):,} linhas de estoque"
            f"</span>".replace(",", "."),
            unsafe_allow_html=True,
        )
    elif tem_ultima and not forcar_exemplo:
        vendas, estoque, dcentro, classificacao = carregar_ultima(tipo_default)
        if f_class:
            classificacao = load_classificacao_produtos(f_class)
            _write_upload(f_class, ULTIMA / "classificacao.csv")
        st.markdown(
            f'<span class="sb-chip">salva</span> '
            f'<span style="color:{SB["green"]}">'
            f"Carregando última atualização ({formatar_data_meta(meta)}) · "
            f"{len(vendas):,} vendas · {len(estoque):,} estoque"
            f"</span>".replace(",", "."),
            unsafe_allow_html=True,
        )
    elif tem_publicada and not forcar_exemplo:
        vendas, estoque, dcentro, classificacao = carregar_publicada(tipo_default)
        st.markdown(
            f'<span class="sb-chip">publicada</span> '
            f'<span style="color:{SB["green"]}">'
            f"Carregando snapshot compartilhado ({formatar_data_meta(meta_pub)}) · "
            f"{len(vendas):,} vendas · {len(estoque):,} estoque"
            f"</span>".replace(",", "."),
            unsafe_allow_html=True,
        )
    elif forcar_exemplo:
        vendas, estoque, dcentro = _load_defaults()
        vendas = vendas.assign(tipo=tipo_default)
        estoque = estoque.assign(tipo=tipo_default)
        st.markdown(
            f'<span class="sb-chip">exemplo</span> <span style="color:{SB["green"]}">kits de exemplo carregados</span>',
            unsafe_allow_html=True,
        )
        if f_class:
            classificacao = load_classificacao_produtos(f_class)
    else:
        st.warning("Envie **ABC Vendas** e **Saldo estoque**, ou ative o exemplo.")
        return None, None, None, None

    return vendas, estoque, dcentro, classificacao



def filters_panel(base: pd.DataFrame) -> pd.DataFrame:
    """Filtros na aba Dados — sempre acessíveis, sem depender da sidebar."""
    st.markdown('<p class="sb-section-title">Filtros</p>', unsafe_allow_html=True)

    tipos = sorted(base["tipo"].dropna().unique().tolist())
    pracas = sorted(base["praca"].dropna().unique().tolist())
    canais = sorted(base["canal"].dropna().unique().tolist())

    if st.button("Restaurar todos os filtros", key="btn_reset_filtros"):
        for key in ("filtro_tipo", "filtro_praca", "filtro_canal", "filtro_busca"):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_tipos = st.multiselect("Tipo", tipos, default=tipos, key="filtro_tipo")
    with c2:
        sel_pracas = st.multiselect("Praça", pracas, default=pracas, key="filtro_praca")
    with c3:
        sel_canais = st.multiselect("Canal", canais, default=canais, key="filtro_canal")

    busca = st.text_input("Buscar SKU / descrição / loja", key="filtro_busca")

    if not sel_tipos:
        sel_tipos = tipos
    if not sel_pracas:
        sel_pracas = pracas
    if not sel_canais:
        sel_canais = canais

    filtered = base[
        base["tipo"].isin(sel_tipos)
        & base["praca"].isin(sel_pracas)
        & base["canal"].isin(sel_canais)
    ]
    if str(busca).strip():
        q = str(busca).strip().lower()
        filtered = filtered[
            filtered["codigo"].str.lower().str.contains(q, na=False)
            | filtered["descricao"].str.lower().str.contains(q, na=False)
            | filtered["loja"].astype(str).str.lower().str.contains(q, na=False)
        ]

    st.caption(
        f"Filtro ativo: {len(filtered):,} linhas · {filtered['bcps'].nunique()} lojas · "
        f"{filtered['codigo'].nunique()} SKUs".replace(",", ".")
    )
    return filtered


def tab_dados() -> pd.DataFrame | None:
    vendas, estoque, dcentro, classificacao = load_data_panel()
    if vendas is None:
        return None

    st.session_state["vendas_raw"] = vendas
    st.session_state["dcentro_raw"] = dcentro

    base = build_base_giro(vendas, estoque, dcentro, classificacao)
    filtered = filters_panel(base)

    st.markdown("---")
    st.markdown('<p class="sb-section-title">Prévia da base cruzada</p>', unsafe_allow_html=True)
    preview = filtered[
        ["bcps", "loja", "praca", "canal", "codigo", "descricao", "vendida", "estoque", "giro", "faturamento"]
    ].head(50)
    show_table(preview, money_cols=["faturamento"], pct_cols=["giro"], height=320)
    return filtered


def dataframe_export(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    export = df.copy()
    export = export.rename(columns={"disponivel": "Estoque Atendido"})
    if "giro" in export.columns:
        export["giro_%"] = (export["giro"] * 100).round(2)
    export.to_excel(buffer, index=False)
    return buffer.getvalue()


def show_table(
    df: pd.DataFrame,
    money_cols: list[str] | None = None,
    pct_cols: list[str] | None = None,
    height: int | None = None,
) -> None:
    """Exibe tabela com números ordenáveis e formatação BR (1.234 / R$ 1.234,56)."""
    money_cols = [c for c in (money_cols or []) if c in df.columns]
    pct_cols = [c for c in (pct_cols or []) if c in df.columns]
    int_cols = [
        c
        for c in ["vendida", "estoque", "disponivel", "skus", "lojas", "Quantidade"]
        if c in df.columns and c not in money_cols and c not in pct_cols
    ]
    show = df.copy()
    config: dict = {}
    formatters: dict = {}

    for col in pct_cols:
        show[col] = pd.to_numeric(show[col], errors="coerce") * 100.0
        config[col] = st.column_config.NumberColumn(col, format="%.1f%%")

    money_labels = {
        "faturamento": "Faturamento",
        "preco_venda": "Preço de venda",
        "valor_estoque": "Valor estoque",
        "Preço de venda": "Preço de venda",
        "Valor estoque": "Valor estoque",
    }
    for col in money_cols:
        show[col] = pd.to_numeric(show[col], errors="coerce")
        config[col] = st.column_config.NumberColumn(
            money_labels.get(col, col.replace("_", " ").title()),
            help="Valores em reais (R$)",
            width="medium",
        )
        formatters[col] = lambda x: fmt_money(float(x)) if pd.notna(x) else "—"

    int_labels = {
        "disponivel": "Estoque Atendido",
        "Quantidade": "Quantidade",
    }
    for col in int_cols:
        show[col] = pd.to_numeric(show[col], errors="coerce")
        # Sem format= no NumberColumn — o Styler aplica 1.234
        rotulo = int_labels.get(col, col)
        config[col] = st.column_config.NumberColumn(rotulo)
        formatters[col] = lambda x: fmt_int(float(x)) if pd.notna(x) else "—"

    for col in show.columns:
        if col in config:
            continue
        if pd.api.types.is_numeric_dtype(show[col]):
            config[col] = st.column_config.NumberColumn(col)

    display_obj: pd.DataFrame | pd.io.formats.style.Styler = show
    if formatters:
        display_obj = show.style.format(formatters, na_rep="—")

    kwargs = {
        "data": display_obj,
        "use_container_width": True,
        "hide_index": True,
        "column_config": config,
    }
    if height is not None:
        kwargs["height"] = height
    st.dataframe(**kwargs)


def tab_visao_geral(filtered: pd.DataFrame) -> None:
    por_praca = aggregate(filtered, ["praca"])
    por_canal = aggregate(filtered, ["canal"])
    por_prod = aggregate(filtered, ["codigo", "descricao", "tipo"])
    alertas = risk_flags(por_prod)

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            por_praca,
            x="praca",
            y="giro",
            title="Giro por praça",
            text=por_praca["giro"].map(lambda x: f"{x * 100:.1f}%"),
            labels={"praca": "Praça", "giro": "Giro"},
            color_discrete_sequence=[SB["green"]],
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(yaxis_tickformat=".0%", showlegend=False)
        st.plotly_chart(plotly_layout(fig, 320), use_container_width=True)

        fig2 = go.Figure()
        order = por_praca.sort_values("vendida", ascending=False)
        fig2.add_bar(name="Vendida", x=order["praca"], y=order["vendida"], marker_color=SB["green"])
        fig2.add_bar(name="Estoque", x=order["praca"], y=order["estoque"], marker_color=SB["blue"])
        fig2.update_layout(barmode="group", title="Vendida vs estoque por praça", yaxis_title="Quantidade")
        st.plotly_chart(plotly_layout(fig2, 320), use_container_width=True)

    with right:
        fig3 = px.bar(
            por_canal,
            x="canal",
            y="giro",
            title="Giro por canal",
            text=por_canal["giro"].map(lambda x: f"{x * 100:.1f}%"),
            labels={"canal": "Canal", "giro": "Giro"},
            color_discrete_sequence=[SB["blue"]],
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(yaxis_tickformat=".0%", showlegend=False)
        st.plotly_chart(plotly_layout(fig3, 320), use_container_width=True)

        share = (
            filtered.groupby("praca", as_index=False)["vendida"]
            .sum()
            .sort_values("vendida", ascending=False)
        )
        fig4 = px.pie(
            share,
            names="praca",
            values="vendida",
            title="Distribuição de vendas por praça",
            color_discrete_sequence=PLOTLY_COLORS,
        )
        fig4.update_traces(textposition="inside", textinfo="percent+label", hole=0.45)
        st.plotly_chart(plotly_layout(fig4, 320), use_container_width=True)

    st.markdown('<p class="sb-section-title">Alertas de produto</p>', unsafe_allow_html=True)
    st.caption("Cadência: &lt; 55% sobra alta · até 75% sobra moderada · acima de 75% giro saudável")
    counts = alertas["alerta"].value_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risco sobra alto", int(counts.get("risco_sobra_alto", 0)))
    c2.metric("Risco sobra moderado", int(counts.get("risco_sobra_moderado", 0)))
    c3.metric("Giro saudável", int(counts.get("giro_saudavel", 0)))
    c4.metric("Ruptura", int(counts.get("ruptura", 0)))

    show_table(
        alertas[["alerta", "tipo", "codigo", "descricao", "vendida", "estoque", "giro", "faturamento"]],
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=360,
    )


def tab_produtos(filtered: pd.DataFrame) -> None:
    por_prod = aggregate(filtered, ["codigo", "descricao", "tipo"])
    alertas = risk_flags(por_prod)

    c1, c2 = st.columns([2, 1])
    with c1:
        ordem = st.radio(
            "Ordenar por",
            ["Maior giro", "Menor giro", "Maior venda", "Maior estoque", "Maior faturamento"],
            horizontal=True,
        )
    with c2:
        alerta_filtro = st.multiselect(
            "Alerta",
            options=sorted(alertas["alerta"].unique()),
            default=sorted(alertas["alerta"].unique()),
        )

    sort_map = {
        "Maior giro": ("giro", False),
        "Menor giro": ("giro", True),
        "Maior venda": ("vendida", False),
        "Maior estoque": ("estoque", False),
        "Maior faturamento": ("faturamento", False),
    }
    col, asc = sort_map[ordem]
    view = alertas[alertas["alerta"].isin(alerta_filtro)].sort_values(col, ascending=asc)

    left, right = st.columns([1.2, 1])
    with left:
        chart_df = view.head(20).sort_values("giro", ascending=True)
        fig = px.bar(
            chart_df,
            x="giro",
            y="descricao",
            orientation="h",
            title="Produtos (até 20) — giro",
            labels={"giro": "Giro", "descricao": "Produto"},
            color="giro",
            color_continuous_scale=[[0, SB["blue"]], [1, SB["green"]]],
        )
        fig.update_layout(xaxis_tickformat=".0%", coloraxis_showscale=False, yaxis_title="")
        st.plotly_chart(plotly_layout(fig, 560), use_container_width=True)

    with right:
        st.markdown('<p class="sb-section-title">Detalhe do produto</p>', unsafe_allow_html=True)
        options = [f"{r.codigo} — {r.descricao}" for r in view.itertuples()]
        if not options:
            st.warning("Nenhum produto no filtro.")
            return
        escolhido = st.selectbox("Selecionar SKU", options)
        codigo = escolhido.split(" — ", 1)[0]
        row = view[view["codigo"] == codigo].iloc[0]
        st.markdown(
            f"""
            <div class="sb-formula">
              <strong>{row['descricao']}</strong><br/>
              Código {row['codigo']} · tipo {row['tipo']} · alerta <strong>{row['alerta']}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Giro", fmt_pct(row["giro"]))
        m2.metric("Vendida", fmt_int(row["vendida"]))
        m3.metric("Estoque", fmt_int(row["estoque"]))

        det = filtered[filtered["codigo"] == codigo]
        por_loja_sku = aggregate(det, ["bcps", "loja", "praca", "canal"]).sort_values("giro", ascending=False)
        st.caption("Distribuição deste SKU por loja")
        show_table(
        por_loja_sku[["loja", "praca", "canal", "vendida", "estoque", "giro", "faturamento"]],
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=320,
    )

    st.markdown('<p class="sb-section-title">Tabela completa de produtos</p>', unsafe_allow_html=True)
    show_table(
        view[
                [
                    "alerta",
                    "tipo",
                    "codigo",
                    "descricao",
                    "vendida",
                    "estoque",
                    "disponivel",
                    "giro",
                    "faturamento",
                    "participacao_venda",
                    "lojas",
                ]
            ],
        money_cols=["faturamento"],
        pct_cols=["giro", "participacao_venda"],
        height=420,
    )
    st.download_button(
        "Baixar produtos (.xlsx)",
        data=dataframe_export(view),
        file_name="giro_por_produto.xlsx",
    )


def tab_lojas(filtered: pd.DataFrame) -> None:
    por_loja = aggregate(filtered, ["bcps", "loja", "praca", "canal", "cluster"])

    t_rank, t_loja, t_praca = st.tabs(
        ["Ranking de lojas", "Detalhe por loja", "Detalhe por praça"]
    )

    with t_rank:
        c1, c2, c3 = st.columns(3)
        with c1:
            praca_f = st.multiselect(
                "Filtrar praça",
                sorted(por_loja["praca"].unique()),
                default=None,
                key="lojas_rank_praca",
            )
        with c2:
            canal_f = st.multiselect(
                "Filtrar canal",
                sorted(por_loja["canal"].unique()),
                default=None,
                key="lojas_rank_canal",
            )
        with c3:
            ordem = st.selectbox(
                "Ordenar",
                ["Maior giro", "Menor giro", "Maior venda", "Maior estoque"],
                key="lojas_rank_ordem",
            )

        view = por_loja.copy()
        if praca_f:
            view = view[view["praca"].isin(praca_f)]
        if canal_f:
            view = view[view["canal"].isin(canal_f)]

        sort_map = {
            "Maior giro": ("giro", False),
            "Menor giro": ("giro", True),
            "Maior venda": ("vendida", False),
            "Maior estoque": ("estoque", False),
        }
        col, asc = sort_map[ordem]
        view = view.sort_values(col, ascending=asc)

        fig = px.scatter(
            view,
            x="estoque",
            y="vendida",
            size="disponivel",
            color="praca",
            hover_name="loja",
            hover_data={"giro": ":.1%", "canal": True, "bcps": True},
        title="Lojas: vendida × estoque (tamanho = estoque atendido)",
        labels={"estoque": "Estoque", "vendida": "Vendida", "praca": "Praça", "disponivel": "Estoque Atendido"},
            color_discrete_sequence=PLOTLY_COLORS,
        )
        st.plotly_chart(plotly_layout(fig, 420), use_container_width=True)

        st.markdown('<p class="sb-section-title">Ranking de lojas</p>', unsafe_allow_html=True)
        show_table(
            view[["bcps", "loja", "praca", "canal", "cluster", "vendida", "estoque", "giro", "faturamento", "skus"]],
            money_cols=["faturamento"],
            pct_cols=["giro"],
            height=440,
        )
        st.download_button(
            "Baixar lojas (.xlsx)",
            data=dataframe_export(view),
            file_name="giro_por_loja.xlsx",
            key="dl_lojas_rank",
        )

    with t_loja:
        st.markdown('<p class="sb-section-title">Detalhe da loja</p>', unsafe_allow_html=True)
        st.caption("Giro de cada kit dentro da loja selecionada.")

        view_all = por_loja.sort_values("giro", ascending=False)
        opcoes = [f"{r.bcps} — {r.loja}" for r in view_all.itertuples()]
        if not opcoes:
            st.warning("Nenhuma loja disponível.")
        else:
            escolha = st.selectbox("Selecionar loja", opcoes, key="detalhe_loja_sel")
            bcps = escolha.split(" — ", 1)[0]
            loja_row = view_all[view_all["bcps"] == bcps].iloc[0]
            st.markdown(
                f"""
                <div class="sb-formula">
                  <strong>{loja_row['loja']}</strong><br/>
                  BCPS {loja_row['bcps']} · {loja_row['praca']} · {loja_row['canal']}
                </div>
                """,
                unsafe_allow_html=True,
            )
            a, b, c, d = st.columns(4)
            a.metric("Giro", fmt_pct(loja_row["giro"]))
            b.metric("Vendida", fmt_int(loja_row["vendida"]))
            c.metric("Estoque", fmt_int(loja_row["estoque"]))
            d.metric("Faturamento", fmt_money(loja_row["faturamento"]))

            skus_loja = aggregate(
                filtered[filtered["bcps"] == bcps], ["codigo", "descricao", "tipo"]
            ).sort_values("giro", ascending=False)
            st.caption(f"SKUs / kits nesta loja · {len(skus_loja)} itens")
            show_table(
                skus_loja[["codigo", "descricao", "tipo", "vendida", "estoque", "disponivel", "giro", "faturamento"]],
                money_cols=["faturamento"],
                pct_cols=["giro"],
                height=480,
            )
            st.download_button(
                "Baixar kits da loja (.xlsx)",
                data=dataframe_export(skus_loja),
                file_name=f"kits_loja_{bcps}.xlsx",
                key="dl_kits_loja",
            )

    with t_praca:
        st.markdown('<p class="sb-section-title">Detalhe por praça</p>', unsafe_allow_html=True)
        st.caption("Mesmo nível de detalhe do giro por kit, consolidado na praça — e por loja dentro dela.")

        pracas = sorted(filtered["praca"].dropna().unique().tolist())
        if not pracas:
            st.warning("Nenhuma praça disponível.")
        else:
            praca_sel = st.selectbox("Selecionar praça", pracas, key="detalhe_praca_loja_sel")
            subset = filtered[filtered["praca"] == praca_sel]
            stats = summarize(subset)

            st.markdown(
                f"""
                <div class="sb-formula">
                  <strong>{praca_sel}</strong><br/>
                  {stats["lojas"]} lojas · {stats["skus"]} kits · panorama da praça
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_kpis_panorama(stats, praca_sel)

            sub_kits, sub_lojas = st.tabs(["Giro por kit na praça", "Giro por loja na praça"])

            with sub_kits:
                kits_praca = aggregate(subset, ["codigo", "descricao", "tipo"]).sort_values(
                    "giro", ascending=False
                )
                st.caption(f"SKUs / kits na praça {praca_sel} · {len(kits_praca)} itens")
                show_table(
                    kits_praca[
                        ["codigo", "descricao", "tipo", "vendida", "estoque", "disponivel", "giro", "faturamento", "lojas"]
                    ],
                    money_cols=["faturamento"],
                    pct_cols=["giro"],
                    height=480,
                )

                # Drill: um kit → como cada loja da praça está
                st.markdown('<p class="sb-section-title">Kit selecionado · lojas da praça</p>', unsafe_allow_html=True)
                kit_opts = [f"{r.codigo} — {r.descricao}" for r in kits_praca.itertuples()]
                if kit_opts:
                    kit_escolha = st.selectbox("Selecionar kit", kit_opts, key="detalhe_praca_kit_sel")
                    cod_kit = kit_escolha.split(" — ", 1)[0]
                    kit_lojas = aggregate(
                        subset[subset["codigo"] == cod_kit],
                        ["bcps", "loja", "canal"],
                    ).sort_values("giro", ascending=False)
                    show_table(
                        kit_lojas[["bcps", "loja", "canal", "vendida", "estoque", "giro", "faturamento"]],
                        money_cols=["faturamento"],
                        pct_cols=["giro"],
                        height=360,
                    )

                st.download_button(
                    "Baixar kits da praça (.xlsx)",
                    data=dataframe_export(kits_praca),
                    file_name=f"kits_praca_{praca_sel}.xlsx".replace(" ", "_"),
                    key="dl_kits_praca_detalhe",
                )

            with sub_lojas:
                lojas_praca = aggregate(subset, ["bcps", "loja", "canal"]).sort_values(
                    "giro", ascending=False
                )
                st.caption(f"Lojas na praça {praca_sel} · {len(lojas_praca)}")
                show_table(
                    lojas_praca[["bcps", "loja", "canal", "vendida", "estoque", "disponivel", "giro", "faturamento", "skus"]],
                    money_cols=["faturamento"],
                    pct_cols=["giro"],
                    height=360,
                )

                st.markdown('<p class="sb-section-title">Loja selecionada · kits na praça</p>', unsafe_allow_html=True)
                loja_opts = [f"{r.bcps} — {r.loja}" for r in lojas_praca.itertuples()]
                if loja_opts:
                    loja_escolha = st.selectbox("Selecionar loja da praça", loja_opts, key="detalhe_praca_loja_inner")
                    bcps_p = loja_escolha.split(" — ", 1)[0]
                    kits_na_loja = aggregate(
                        subset[subset["bcps"] == bcps_p],
                        ["codigo", "descricao", "tipo"],
                    ).sort_values("giro", ascending=False)
                    loja_nome = lojas_praca.loc[lojas_praca["bcps"] == bcps_p, "loja"].iloc[0]
                    st.caption(f"Kits em {loja_nome} ({praca_sel})")
                    show_table(
                        kits_na_loja[
                            ["codigo", "descricao", "tipo", "vendida", "estoque", "disponivel", "giro", "faturamento"]
                        ],
                        money_cols=["faturamento"],
                        pct_cols=["giro"],
                        height=420,
                    )

                st.download_button(
                    "Baixar lojas da praça (.xlsx)",
                    data=dataframe_export(lojas_praca),
                    file_name=f"lojas_praca_{praca_sel}.xlsx".replace(" ", "_"),
                    key="dl_lojas_praca_detalhe",
                )


def tab_pracas(filtered: pd.DataFrame) -> None:
    por_praca = aggregate(filtered, ["praca"])
    st.markdown('<p class="sb-section-title">Resumo por praça</p>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_bar(name="Vendida", x=por_praca["praca"], y=por_praca["vendida"], marker_color=SB["green"])
    fig.add_bar(name="Estoque", x=por_praca["praca"], y=por_praca["estoque"], marker_color=SB["blue"])
    fig.update_layout(barmode="group", title="Volume por praça", yaxis_title="Quantidade")
    st.plotly_chart(plotly_layout(fig, 340), use_container_width=True)

    show_table(
        por_praca[["praca", "vendida", "estoque", "disponivel", "giro", "faturamento", "participacao_venda", "lojas", "skus"]],
        money_cols=["faturamento"],
        pct_cols=["giro", "participacao_venda"],
    )

    st.markdown('<p class="sb-section-title">Drill-down da praça</p>', unsafe_allow_html=True)
    praca_sel = st.selectbox("Praça", sorted(filtered["praca"].unique()))
    subset = filtered[filtered["praca"] == praca_sel]

    c1, c2, c3, c4 = st.columns(4)
    s = summarize(subset)
    c1.metric("Giro", fmt_pct(s["giro"]))
    c2.metric("Vendida", fmt_int(s["vendida"]))
    c3.metric("Estoque", fmt_int(s["estoque"]))
    c4.metric("Lojas", fmt_int(s["lojas"]))

    t1, t2 = st.tabs(["Lojas da praça", "Produtos da praça"])
    with t1:
        lojas = aggregate(subset, ["bcps", "loja", "canal"]).sort_values("giro", ascending=False)
        show_table(
        lojas[["bcps", "loja", "canal", "vendida", "estoque", "giro", "faturamento", "skus"]],
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=400,
    )
    with t2:
        prods = aggregate(subset, ["codigo", "descricao", "tipo"]).sort_values("giro", ascending=False)
        show_table(
        prods[["codigo", "descricao", "tipo", "vendida", "estoque", "giro", "faturamento", "lojas"]],
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=400,
    )


def tab_canais(filtered: pd.DataFrame) -> None:
    por_canal = aggregate(filtered, ["canal"])
    cruzado = aggregate(filtered, ["canal", "praca"])

    left, right = st.columns(2)
    with left:
        show_table(
        por_canal[["canal", "vendida", "estoque", "giro", "faturamento", "participacao_venda", "lojas", "skus"]],
        money_cols=["faturamento"],
        pct_cols=["giro", "participacao_venda"],
    )
    with right:
        fig = px.density_heatmap(
            cruzado,
            x="canal",
            y="praca",
            z="giro",
            title="Giro: canal × praça",
            color_continuous_scale=[[0, SB["bg"]], [0.4, SB["blue"]], [1, SB["green"]]],
            labels={"giro": "Giro", "canal": "Canal", "praca": "Praça"},
        )
        fig.update_traces(hovertemplate="Canal=%{x}<br>Praça=%{y}<br>Giro=%{z:.1%}<extra></extra>")
        st.plotly_chart(plotly_layout(fig, 360), use_container_width=True)

    st.markdown('<p class="sb-section-title">Matriz detalhada canal × praça</p>', unsafe_allow_html=True)
    show_table(
        cruzado.sort_values(["canal", "giro"], ascending=[True, False])[
                ["canal", "praca", "vendida", "estoque", "giro", "faturamento", "lojas", "skus"]
            ],
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=420,
    )

    canal_sel = st.selectbox("Detalhar canal", sorted(filtered["canal"].unique()))
    subset = filtered[filtered["canal"] == canal_sel]
    lojas = aggregate(subset, ["bcps", "loja", "praca"]).sort_values("giro", ascending=False)
    st.caption(f"Lojas do canal {canal_sel}")
    show_table(
        lojas[["bcps", "loja", "praca", "vendida", "estoque", "giro", "faturamento"]],
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=360,
    )


def faixa_preco_p1_p5(precos: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """Segmenta preços em 5 faixas: P1 (mais baratos) … P5 (mais caros).

    Usa quintis sobre os preços únicos de SKU (> 0). Retorna a série de
    faixas alinhada a `precos` e um resumo com intervalo de cada Pn.
    """
    labels = ["P1", "P2", "P3", "P4", "P5"]
    out = pd.Series("Sem preço", index=precos.index, dtype=object)
    valid = pd.to_numeric(precos, errors="coerce").fillna(0.0)
    mask = valid > 0
    if not mask.any():
        resumo = pd.DataFrame(columns=["faixa", "preco_min", "preco_max", "skus"])
        return out, resumo

    unicos = valid.loc[mask].drop_duplicates().sort_values()
    n_bins = min(5, unicos.nunique())
    if n_bins < 2:
        out.loc[mask] = "P1"
        resumo = pd.DataFrame(
            [{"faixa": "P1", "preco_min": float(unicos.min()), "preco_max": float(unicos.max()), "skus": int(mask.sum())}]
        )
        return out, resumo

    try:
        faixas_unicos = pd.qcut(unicos, q=n_bins, labels=labels[:n_bins], duplicates="drop")
    except ValueError:
        faixas_unicos = pd.cut(unicos, bins=n_bins, labels=labels[:n_bins], include_lowest=True)

    mapa = dict(zip(unicos.values, faixas_unicos.astype(str).values))
    out.loc[mask] = valid.loc[mask].map(mapa).fillna("Sem preço")

    resumo_rows = []
    for faixa in labels[:n_bins]:
        precos_f = unicos[faixas_unicos.astype(str) == faixa]
        if precos_f.empty:
            continue
        resumo_rows.append(
            {
                "faixa": faixa,
                "preco_min": float(precos_f.min()),
                "preco_max": float(precos_f.max()),
                "skus": int((out == faixa).sum()),
            }
        )
    return out, pd.DataFrame(resumo_rows)


def tab_estoque(filtered: pd.DataFrame) -> None:
    """Base de estoque: loja, quantidade, SKU, descrição e preço de venda."""
    st.markdown('<p class="sb-section-title">Base de estoque</p>', unsafe_allow_html=True)
    st.caption(
        "Estoque por loja e SKU, com descrição e preço de venda da base de saldo. "
        "Faixas P1–P5: P1 = kits mais baratos, P5 = mais caros (quintis por preço de SKU). "
        "Respeita os filtros da aba Dados."
    )

    show = filtered.copy()
    if "preco_venda" not in show.columns:
        show["preco_venda"] = 0.0

    # Faixa calculada por SKU (um preço por código), depois aplicada às linhas loja×SKU
    sku_preco = (
        show.groupby("codigo", as_index=False)["preco_venda"]
        .max()
        .rename(columns={"preco_venda": "preco_sku"})
    )
    faixas_sku, resumo_faixas = faixa_preco_p1_p5(sku_preco["preco_sku"])
    sku_preco["faixa"] = faixas_sku.values
    show = show.merge(sku_preco[["codigo", "faixa"]], on="codigo", how="left")
    show["faixa"] = show["faixa"].fillna("Sem preço")

    c1, c2, c3 = st.columns([1, 1.4, 1.6])
    with c1:
        so_com_estoque = st.toggle("Somente com estoque > 0", value=True, key="estoque_so_positivo")
    with c2:
        opcoes_faixa = ["P1", "P2", "P3", "P4", "P5"]
        if (show["faixa"] == "Sem preço").any():
            opcoes_faixa = opcoes_faixa + ["Sem preço"]
        faixas_sel = st.multiselect(
            "Faixa de preço",
            options=opcoes_faixa,
            default=["P1", "P2", "P3", "P4", "P5"],
            key="estoque_faixas",
            help="P1 = mais baratos · P5 = mais caros",
        )
    with c3:
        busca = st.text_input(
            "Buscar SKU ou descrição",
            value="",
            placeholder="Ex.: 94133 ou ZAAD",
            key="estoque_busca",
        )

    if so_com_estoque:
        show = show[show["estoque"] > 0]
    if faixas_sel:
        show = show[show["faixa"].isin(faixas_sel)]
    if busca.strip():
        q = busca.strip().lower()
        show = show[
            show["codigo"].astype(str).str.lower().str.contains(q, na=False)
            | show["descricao"].astype(str).str.lower().str.contains(q, na=False)
            | show["loja"].astype(str).str.lower().str.contains(q, na=False)
        ]

    show["valor_estoque"] = show["estoque"] * show["preco_venda"]

    if not resumo_faixas.empty:
        legend = " · ".join(
            f"**{r.faixa}** {fmt_money(r.preco_min)}–{fmt_money(r.preco_max)}"
            for r in resumo_faixas.itertuples()
        )
        st.caption(f"Intervalos atuais: {legend}")

    cols = ["faixa", "loja", "codigo", "descricao", "estoque", "preco_venda", "valor_estoque", "praca", "canal"]
    cols = [c for c in cols if c in show.columns]
    show = show[cols].sort_values(["faixa", "loja", "codigo"]).reset_index(drop=True)
    show = show.rename(
        columns={
            "faixa": "Faixa",
            "loja": "Loja",
            "codigo": "SKU",
            "descricao": "Descrição",
            "estoque": "Quantidade",
            "preco_venda": "Preço de venda",
            "valor_estoque": "Valor estoque",
            "praca": "Praça",
            "canal": "Canal",
        }
    )

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Linhas", f"{len(show):,}".replace(",", "."))
    with k2:
        st.metric("Quantidade total", f"{show['Quantidade'].sum():,.0f}".replace(",", "."))
    with k3:
        total_valor = float(show["Valor estoque"].sum()) if "Valor estoque" in show.columns else 0.0
        st.metric("Valor em estoque", fmt_money(total_valor))

    if not show.empty and "Faixa" in show.columns:
        por_faixa = (
            show.groupby("Faixa", as_index=False)
            .agg(
                SKUs=("SKU", "nunique"),
                Quantidade=("Quantidade", "sum"),
                **{"Valor estoque": ("Valor estoque", "sum")},
            )
        )
        ordem = {f: i for i, f in enumerate(["P1", "P2", "P3", "P4", "P5", "Sem preço"])}
        por_faixa = por_faixa.sort_values("Faixa", key=lambda s: s.map(ordem))
        st.markdown('<p class="sb-section-title">Resumo por faixa</p>', unsafe_allow_html=True)
        show_table(por_faixa, money_cols=["Valor estoque"], height=220)

    st.caption(f"{len(show):,} linhas".replace(",", "."))
    show_table(
        show,
        money_cols=["Preço de venda", "Valor estoque"],
        height=520,
    )
    st.download_button(
        "Baixar base de estoque (.xlsx)",
        data=dataframe_export(show),
        file_name="base_estoque.xlsx",
        key="dl_estoque",
    )


def tab_base(filtered: pd.DataFrame) -> None:
    st.markdown(
        f"""
        <div class="sb-formula">
          Linha = <strong>loja × SKU</strong>. Giro calculado em cada combinação.
          Use os filtros da barra lateral e a busca abaixo para aprofundar.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        min_giro, max_giro = st.slider("Faixa de giro (%)", 0.0, 100.0, (0.0, 100.0), 1.0)
    with c2:
        so_com_venda = st.toggle("Somente com venda > 0", value=False)
    with c3:
        so_com_estoque = st.toggle("Somente com estoque > 0", value=False)

    show = filtered.copy()
    show = show[(show["giro"].fillna(0) * 100 >= min_giro) & (show["giro"].fillna(0) * 100 <= max_giro)]
    if so_com_venda:
        show = show[show["vendida"] > 0]
    if so_com_estoque:
        show = show[show["estoque"] > 0]

    cols = [
        "tipo",
        "bcps",
        "loja",
        "praca",
        "canal",
        "cluster",
        "codigo",
        "descricao",
        "vendida",
        "estoque",
        "disponivel",
        "giro",
        "faturamento",
    ]
    show = show[cols].sort_values(["praca", "loja", "giro"], ascending=[True, True, False])

    st.caption(f"{len(show):,} linhas".replace(",", "."))
    show_table(
        show,
        money_cols=["faturamento"],
        pct_cols=["giro"],
        height=520,
    )
    st.download_button(
        "Baixar base completa (.xlsx)",
        data=dataframe_export(show),
        file_name="giro_base_detalhada.xlsx",
    )


def _vendas_com_data_ok(vendas) -> bool:
    if vendas is None or getattr(vendas, "empty", True):
        return False
    if "data" not in vendas.columns:
        return False
    datas = pd.to_datetime(vendas["data"], dayfirst=True, errors="coerce")
    return bool(datas.notna().any())


def preparar_vendas_diarias(vendas: pd.DataFrame, dcentro: pd.DataFrame, filtered: pd.DataFrame) -> pd.DataFrame:
    """Enriquece vendas diárias com praça/canal e aplica o mesmo recorte de lojas/SKUs do filtro."""
    if not _vendas_com_data_ok(vendas):
        return pd.DataFrame()

    v = vendas.copy()
    v["data"] = pd.to_datetime(v["data"], dayfirst=True, errors="coerce")
    v = v.dropna(subset=["data"]).copy()
    v["data"] = v["data"].dt.normalize()
    v["bcps"] = v["bcps"].astype(str)
    v["codigo"] = v["codigo"].astype(str)

    v = v.merge(dcentro, on="bcps", how="left")
    if "loja_dc" in v.columns:
        v["loja"] = v["loja_dc"].fillna(v["loja_origem"]).fillna(v["bcps"])
    else:
        v["loja"] = v["loja_origem"].fillna(v["bcps"])
    if "praca" not in v.columns:
        v["praca"] = "Sem praça"
    else:
        v["praca"] = v["praca"].fillna("Sem praça")
    if "canal" not in v.columns:
        v["canal"] = "Sem canal"
    else:
        v["canal"] = v["canal"].fillna("Sem canal")

    # Mantém só combinações loja×SKU presentes no filtro atual
    chaves = filtered[["bcps", "codigo"]].drop_duplicates().copy()
    chaves["bcps"] = chaves["bcps"].astype(str)
    chaves["codigo"] = chaves["codigo"].astype(str)
    v = v.merge(chaves, on=["bcps", "codigo"], how="inner")
    return v


def tab_vendas_dia(filtered: pd.DataFrame) -> None:
    """Análise de vendas por dia (coluna Quebra do ABC)."""
    st.markdown('<p class="sb-section-title">Vendas por dia</p>', unsafe_allow_html=True)
    st.caption("Usa a data da coluna Quebra do ABC Vendas. Sempre lê a base salva no disco (não depende da memória da sessão).")

    # Sempre carregar do disco — sessão/cache pode ficar sem a coluna data
    tipo = st.session_state.get("tipo_default", "kit")
    vendas = None
    dcentro = None
    origem = None

    if ultima_disponivel():
        try:
            vendas, _estoque, dcentro, _clas = carregar_ultima(tipo)
            origem = "última base salva (data/ultima)"
        except Exception as exc:
            st.error(f"Erro ao ler data/ultima: {exc}")

    if not _vendas_com_data_ok(vendas):
        try:
            vendas = load_vendas(EXEMPLO / "vendas_abc_kits.csv", tipo=tipo)
            dcentro = load_dcentro(DATA / "dcentros.csv")
            origem = "base de exemplo"
        except Exception as exc:
            st.error(f"Erro ao ler exemplo: {exc}")

    if not _vendas_com_data_ok(vendas):
        st.warning(
            "Não foi possível ler datas da coluna Quebra. "
            "Na aba **Dados**, envie de novo o ABC Vendas e aguarde a mensagem de salvo."
        )
        st.code(f"Arquivo esperado: {ULTIMA / 'vendas.csv'}\nExiste: {(ULTIMA / 'vendas.csv').exists()}")
        if st.button("Limpar cache e tentar de novo", key="btn_reload_datas"):
            st.cache_data.clear()
            for key in ("vendas_raw", "dcentro_raw", "filtered"):
                st.session_state.pop(key, None)
            st.rerun()
        return

    st.session_state["vendas_raw"] = vendas
    st.session_state["dcentro_raw"] = dcentro
    st.caption(f"Origem das datas: **{origem}** · {int(pd.to_datetime(vendas['data'], errors='coerce').notna().sum())} linhas com data")

    diarias = preparar_vendas_diarias(vendas, dcentro, filtered)
    if diarias.empty:
        # Fallback: ignora cruzamento loja×SKU do filtro e usa só praça/canal
        st.info("Exibindo vendas diárias da base (sem cruzamento fino do filtro de giro).")
        v = vendas.copy()
        v["data"] = pd.to_datetime(v["data"], dayfirst=True, errors="coerce")
        v = v.dropna(subset=["data"]).copy()
        v["data"] = v["data"].dt.normalize()
        v["bcps"] = v["bcps"].astype(str)
        v = v.merge(dcentro, on="bcps", how="left")
        if "loja_dc" in v.columns:
            v["loja"] = v["loja_dc"].fillna(v["loja_origem"]).fillna(v["bcps"])
        else:
            v["loja"] = v["loja_origem"].fillna(v["bcps"])
        v["praca"] = v["praca"].fillna("Sem praça") if "praca" in v.columns else "Sem praça"
        v["canal"] = v["canal"].fillna("Sem canal") if "canal" in v.columns else "Sem canal"
        if filtered is not None and not filtered.empty:
            pracas_ok = set(filtered["praca"].dropna().unique())
            canais_ok = set(filtered["canal"].dropna().unique())
            v = v[v["praca"].isin(pracas_ok) & v["canal"].isin(canais_ok)]
        diarias = v

    if diarias.empty:
        st.warning("Nenhuma venda com data após aplicar os filtros.")
        return

    diarias = diarias.copy()
    diarias["data"] = pd.to_datetime(diarias["data"]).dt.date
    dias = sorted(diarias["data"].dropna().unique().tolist())
    pracas = sorted(diarias["praca"].dropna().unique().tolist())
    canais = sorted(diarias["canal"].dropna().unique().tolist())

    # Inclui automaticamente dias/praças/canais novos que ainda não existiam no filtro
    def _incluir_opcoes_novas(chave: str, opcoes: list) -> None:
        opcoes_set = set(opcoes)
        conhecidos = st.session_state.get(f"{chave}_conhecidos")
        if chave in st.session_state:
            if conhecidos is None:
                st.session_state[chave] = list(opcoes)
            else:
                atuais = [item for item in st.session_state[chave] if item in opcoes_set]
                novos = [item for item in opcoes if item not in set(conhecidos)]
                st.session_state[chave] = atuais + novos
        st.session_state[f"{chave}_conhecidos"] = list(opcoes)

    _incluir_opcoes_novas("vdia_dias", dias)
    _incluir_opcoes_novas("vdia_praca", pracas)
    _incluir_opcoes_novas("vdia_canal", canais)

    f1, f2, f3 = st.columns(3)
    with f1:
        dias_sel = st.multiselect(
            "Dias",
            options=dias,
            default=dias,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
            key="vdia_dias",
        )
    with f2:
        pracas_sel = st.multiselect("Praça", pracas, default=pracas, key="vdia_praca")
    with f3:
        canais_sel = st.multiselect("Canal", canais, default=canais, key="vdia_canal")

    if not dias_sel:
        dias_sel = dias
    if not pracas_sel:
        pracas_sel = pracas
    if not canais_sel:
        canais_sel = canais

    view = diarias[
        diarias["data"].isin(dias_sel)
        & diarias["praca"].isin(pracas_sel)
        & diarias["canal"].isin(canais_sel)
    ]
    if view.empty:
        st.warning("Nenhuma venda no recorte selecionado.")
        return

    por_dia = (
        view.groupby("data", as_index=False)
        .agg(
            vendida=("vendida", "sum"),
            faturamento=("faturamento", "sum"),
            lojas=("bcps", "nunique"),
            skus=("codigo", "nunique"),
            linhas=("codigo", "count"),
        )
        .sort_values("data")
    )
    por_dia["ticket_medio"] = por_dia["faturamento"] / por_dia["vendida"].replace(0, pd.NA)

    # Big numbers do período
    tot_vendida = float(por_dia["vendida"].sum())
    tot_fat = float(por_dia["faturamento"].sum())
    media_dia = tot_vendida / len(por_dia) if len(por_dia) else 0
    melhor = por_dia.loc[por_dia["vendida"].idxmax()]
    st.markdown(
        f"""
        <div class="sb-kpi-row sb-kpi-6">
          <div>
            <div class="sb-kpi-value">{len(por_dia)}</div>
            <div class="sb-kpi-label">dias no recorte</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(tot_vendida)}</div>
            <div class="sb-kpi-label">unidades vendidas</div>
          </div>
          <div>
            <div class="sb-kpi-value sb-kpi-money">{fmt_money(tot_fat)}</div>
            <div class="sb-kpi-label">faturamento</div>
          </div>
          <div>
            <div class="sb-kpi-value">{fmt_int(media_dia)}</div>
            <div class="sb-kpi-label">média un./dia</div>
          </div>
          <div>
            <div class="sb-kpi-value">{pd.Timestamp(melhor['data']).strftime('%d/%m')}</div>
            <div class="sb-kpi-label">melhor dia · {fmt_int(melhor['vendida'])} un.</div>
          </div>
          <div>
            <div class="sb-kpi-value sb-kpi-money">{fmt_money(float(melhor['faturamento']))}</div>
            <div class="sb-kpi-label">faturamento do melhor dia</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    g1, g2 = st.columns(2)
    with g1:
        fig_q = go.Figure()
        fig_q.add_bar(
            x=[pd.Timestamp(d).strftime("%d/%m") for d in por_dia["data"]],
            y=por_dia["vendida"],
            marker_color=SB["green"],
            name="Vendida",
        )
        fig_q.update_layout(title="Quantidade vendida por dia", yaxis_title="Unidades")
        st.plotly_chart(plotly_layout(fig_q, 340), use_container_width=True)
    with g2:
        fig_f = go.Figure()
        fig_f.add_bar(
            x=[pd.Timestamp(d).strftime("%d/%m") for d in por_dia["data"]],
            y=por_dia["faturamento"],
            marker_color=SB["blue"],
            name="Faturamento",
        )
        fig_f.update_layout(title="Faturamento por dia", yaxis_title="R$")
        st.plotly_chart(plotly_layout(fig_f, 340), use_container_width=True)

    # Evolução por praça
    por_dia_praca = (
        view.groupby(["data", "praca"], as_index=False)
        .agg(vendida=("vendida", "sum"), faturamento=("faturamento", "sum"))
        .sort_values("data")
    )
    if por_dia_praca["praca"].nunique() > 1:
        por_dia_praca = por_dia_praca.copy()
        por_dia_praca["data"] = pd.to_datetime(por_dia_praca["data"])
        ordem_dias = [
            d.strftime("%d/%m/%Y")
            for d in sorted(por_dia_praca["data"].unique())
        ]
        por_dia_praca["data_label"] = por_dia_praca["data"].dt.strftime("%d/%m/%Y")
        por_dia_praca = por_dia_praca.sort_values(["data", "praca"])
        fig_p = px.line(
            por_dia_praca,
            x="data_label",
            y="vendida",
            color="praca",
            markers=True,
            title="Vendas por dia · por praça",
            labels={"data_label": "Dia", "vendida": "Unidades", "praca": "Praça"},
            color_discrete_sequence=PLOTLY_COLORS,
            category_orders={"data_label": ordem_dias},
        )
        fig_p.update_xaxes(categoryorder="array", categoryarray=ordem_dias)
        st.plotly_chart(plotly_layout(fig_p, 360), use_container_width=True)

    st.markdown('<p class="sb-section-title">Tabela por dia</p>', unsafe_allow_html=True)
    tab_dia = por_dia.copy()
    tab_dia["data"] = tab_dia["data"].map(lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"))
    show_table(
        tab_dia.rename(columns={"ticket_medio": "ticket_medio_un"})[
            ["data", "vendida", "faturamento", "lojas", "skus", "ticket_medio_un"]
        ],
        money_cols=["faturamento", "ticket_medio_un"],
        height=280,
    )

    st.markdown('<p class="sb-section-title">Drill-down do dia</p>', unsafe_allow_html=True)
    dia_escolha = st.selectbox(
        "Selecionar dia",
        options=list(por_dia["data"]),
        format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
        key="vdia_drill_dia",
    )
    dia_df = view[view["data"] == dia_escolha]
    d1, d2, d3 = st.columns(3)
    d1.metric("Vendida no dia", fmt_int(dia_df["vendida"].sum()))
    d2.metric("Faturamento", fmt_money(dia_df["faturamento"].sum()))
    d3.metric("Lojas com venda", fmt_int(dia_df["bcps"].nunique()))

    t_loja, t_kit, t_praca = st.tabs(["Por loja", "Por kit", "Por praça"])
    with t_loja:
        por_loja_dia = (
            dia_df.groupby(["bcps", "loja", "praca", "canal"], as_index=False)
            .agg(vendida=("vendida", "sum"), faturamento=("faturamento", "sum"), skus=("codigo", "nunique"))
            .sort_values("vendida", ascending=False)
        )
        show_table(por_loja_dia, money_cols=["faturamento"], height=400)
    with t_kit:
        por_kit_dia = (
            dia_df.groupby(["codigo", "descricao"], as_index=False)
            .agg(vendida=("vendida", "sum"), faturamento=("faturamento", "sum"), lojas=("bcps", "nunique"))
            .sort_values("vendida", ascending=False)
        )
        show_table(por_kit_dia, money_cols=["faturamento"], height=400)
    with t_praca:
        por_praca_dia = (
            dia_df.groupby(["praca"], as_index=False)
            .agg(
                vendida=("vendida", "sum"),
                faturamento=("faturamento", "sum"),
                lojas=("bcps", "nunique"),
                skus=("codigo", "nunique"),
            )
            .sort_values("vendida", ascending=False)
        )
        show_table(por_praca_dia, money_cols=["faturamento"], height=320)

    st.download_button(
        "Baixar vendas por dia (.xlsx)",
        data=dataframe_export(
            por_dia.assign(data=por_dia["data"].map(lambda d: pd.Timestamp(d).strftime("%d/%m/%Y")))
        ),
        file_name="vendas_por_dia.xlsx",
        key="dl_vendas_dia",
    )


def main():
    inject_theme()
    if not exigir_senha():
        return
    render_header()

    st.sidebar.markdown("### Ajuda")
    st.sidebar.markdown(
        """
        <div class="sb-formula" style="margin-top:0.5rem;">
          Upload e filtros estão na aba <strong>Dados</strong>.<br/><br/>
          Para compartilhar: rode <strong>preparar_publicacao.bat</strong>,
          faça push no GitHub e publique no Streamlit Cloud.<br/><br/>
          Se o painel lateral sumir, clique na seta <strong>▶</strong>
          no canto superior esquerdo da tela.
        </div>
        """,
        unsafe_allow_html=True,
    )

    (
        tab_resumo,
        tab_panorama,
        tab_dia,
        tab_prod,
        tab_loja,
        tab_praca,
        tab_canal,
        tab_estoque_ui,
        tab_detalhe,
        tab_dados_ui,
    ) = st.tabs(
        [
            "Visão geral",
            "Resumo praça",
            "Vendas por dia",
            "Produtos",
            "Lojas",
            "Praças",
            "Canais",
            "Estoque",
            "Base detalhada",
            "Dados",
        ]
    )

    with tab_dados_ui:
        filtered = tab_dados()
        if filtered is not None:
            st.session_state["filtered"] = filtered
            stats = summarize(filtered)
            st.markdown('<p class="sb-section-title">Resumo com filtros atuais</p>', unsafe_allow_html=True)
            render_kpis(stats)

    filtered = st.session_state.get("filtered")
    if filtered is None or getattr(filtered, "empty", True):
        with tab_resumo:
            st.info("Abra a aba **Dados**, carregue as bases (ou use o exemplo) e ajuste os filtros.")
        return

    stats = summarize(filtered)

    with tab_resumo:
        render_kpis(stats)
        tab_visao_geral(filtered)
    with tab_panorama:
        tab_resumo_praca(filtered)
    with tab_dia:
        tab_vendas_dia(filtered)
    with tab_prod:
        tab_produtos(filtered)
    with tab_loja:
        tab_lojas(filtered)
    with tab_praca:
        tab_pracas(filtered)
    with tab_canal:
        tab_canais(filtered)
    with tab_estoque_ui:
        tab_estoque(filtered)
    with tab_detalhe:
        tab_base(filtered)


if __name__ == "__main__":
    main()
