"""Giro calculation and aggregations.

giro = quantidade vendida / (quantidade vendida + estoque atual)
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .loaders import load_classificacao_produtos


def _giro_series(vendida: pd.Series, estoque: pd.Series) -> pd.Series:
    disponivel = vendida + estoque
    return vendida.where(disponivel > 0) / disponivel.where(disponivel > 0)


def build_base_giro(
    vendas: pd.DataFrame,
    estoque: pd.DataFrame,
    dcentro: pd.DataFrame,
    classificacao: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    v = (
        vendas.groupby(["bcps", "codigo", "tipo"], as_index=False)
        .agg(
            vendida=("vendida", "sum"),
            faturamento=("faturamento", "sum"),
            descricao=("descricao", "first"),
            loja_origem=("loja_origem", "first"),
        )
    )
    e = (
        estoque.groupby(["bcps", "codigo", "tipo"], as_index=False)
        .agg(
            estoque=("estoque", "sum"),
            descricao_e=("descricao", "first"),
            loja_e=("loja_origem", "first"),
        )
    )

    base = v.merge(e, on=["bcps", "codigo", "tipo"], how="outer")
    base["vendida"] = base["vendida"].fillna(0.0)
    base["estoque"] = base["estoque"].fillna(0.0)
    base["faturamento"] = base["faturamento"].fillna(0.0)
    base["descricao"] = base["descricao"].fillna(base["descricao_e"]).fillna("")
    base["loja_origem"] = base["loja_origem"].fillna(base["loja_e"])
    base = base.drop(columns=["descricao_e", "loja_e"], errors="ignore")

    if classificacao is not None and not classificacao.empty:
        base = base.drop(columns=["tipo"], errors="ignore")
        base = base.merge(classificacao, on="codigo", how="left")
        base["tipo"] = base["tipo"].fillna("nao_classificado")

    base = base.merge(dcentro, on="bcps", how="left")
    base["loja"] = base["loja_dc"].fillna(base["loja_origem"]).fillna(base["bcps"])
    base["praca"] = base["praca"].fillna("Sem praça")
    base["canal"] = base["canal"].fillna("Sem canal")
    base["cluster"] = base.get("cluster", pd.Series(["Sem cluster"] * len(base))).fillna("Sem cluster")
    base["disponivel"] = base["vendida"] + base["estoque"]
    base["giro"] = _giro_series(base["vendida"], base["estoque"])
    base["cobertura_dias"] = base.apply(
        lambda r: (r["estoque"] / r["vendida"]) if r["vendida"] > 0 else None,
        axis=1,
    )
    return base


def aggregate(base: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    grouped = (
        base.groupby(by, as_index=False)
        .agg(
            vendida=("vendida", "sum"),
            estoque=("estoque", "sum"),
            faturamento=("faturamento", "sum"),
            skus=("codigo", "nunique"),
            lojas=("bcps", "nunique"),
        )
    )
    grouped["disponivel"] = grouped["vendida"] + grouped["estoque"]
    grouped["giro"] = _giro_series(grouped["vendida"], grouped["estoque"])
    grouped["participacao_venda"] = grouped["vendida"] / grouped["vendida"].sum()
    grouped["participacao_fat"] = grouped["faturamento"] / grouped["faturamento"].replace(0, pd.NA)
    return grouped.sort_values("giro", ascending=False).reset_index(drop=True)


def summarize(base: pd.DataFrame) -> dict:
    vendida = float(base["vendida"].sum())
    estoque = float(base["estoque"].sum())
    disponivel = vendida + estoque
    return {
        "vendida": vendida,
        "estoque": estoque,
        "disponivel": disponivel,
        "giro": (vendida / disponivel) if disponivel > 0 else None,
        "faturamento": float(base["faturamento"].sum()),
        "skus": int(base["codigo"].nunique()),
        "lojas": int(base["bcps"].nunique()),
        "pracas": int(base["praca"].nunique()),
    }


def risk_flags(base_produto: pd.DataFrame, giro_baixo: float = 0.08, giro_alto: float = 0.25) -> pd.DataFrame:
    df = base_produto.copy()
    df["alerta"] = "normal"
    df.loc[df["giro"].fillna(0) < giro_baixo, "alerta"] = "estoque_parado"
    df.loc[df["giro"].fillna(0) >= giro_alto, "alerta"] = "alto_giro"
    df.loc[(df["estoque"] <= 0) & (df["vendida"] > 0), "alerta"] = "ruptura"
    return df
