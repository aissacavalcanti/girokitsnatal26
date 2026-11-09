"""Data loaders for vendas ABC, saldo de estoque and dCentro."""
from __future__ import annotations

import unicodedata
from io import BytesIO, StringIO
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from .br_numbers import (
    extract_bcps_from_estoque,
    extract_bcps_from_venda,
    extract_loja_nome_from_estoque,
    extract_loja_nome_from_venda,
    normalize_product_code,
    parse_br_number,
)

PathLike = Union[str, Path]
FileInput = Union[PathLike, object]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _norm_name(text: str) -> str:
    return _strip_accents(str(text).strip().lower())


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


def _read_csv(source: FileInput) -> pd.DataFrame:
    """Read semicolon CSV from path or Streamlit UploadedFile."""
    if hasattr(source, "read"):
        raw = source.read()
        if hasattr(source, "seek"):
            source.seek(0)
        for encoding in ("cp1252", "latin-1", "utf-8-sig", "utf-8"):
            try:
                text = raw.decode(encoding) if isinstance(raw, (bytes, bytearray)) else raw
                return _clean_columns(pd.read_csv(StringIO(text), sep=";", dtype=str))
            except UnicodeDecodeError:
                continue
        return _clean_columns(
            pd.read_csv(
                BytesIO(raw),
                sep=";",
                encoding="cp1252",
                dtype=str,
                encoding_errors="replace",
            )
        )

    path = Path(source)
    for encoding in ("utf-8-sig", "cp1252", "latin-1", "utf-8"):
        try:
            return _clean_columns(pd.read_csv(path, sep=";", encoding=encoding, dtype=str))
        except UnicodeDecodeError:
            continue
    return _clean_columns(
        pd.read_csv(path, sep=";", encoding="cp1252", dtype=str, encoding_errors="replace")
    )


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    normalized = {_norm_name(c): c for c in df.columns}
    for name in candidates:
        key = _norm_name(name)
        if key in normalized:
            return normalized[key]
    for name in candidates:
        key = _norm_name(name)
        for col_norm, col in normalized.items():
            if key in col_norm:
                return col
    raise KeyError(
        f"Coluna nao encontrada. Procurado: {candidates}. Disponiveis: {list(df.columns)}"
    )


def load_vendas(path: FileInput, tipo: str = "kit") -> pd.DataFrame:
    df = _read_csv(path)
    col_loja = _find_column(df, ["quebra2", "loja", "pdv"])
    col_cod = _find_column(df, ["codigo", "cod"])
    col_desc = _find_column(df, ["descricao", "desc"])
    col_qtd = _find_column(df, ["quantidade", "qtd"])
    fat_candidates = [c for c in df.columns if "fatur" in _norm_name(c)]
    col_fat = fat_candidates[0] if fat_candidates else None

    # Data do relat?rio ABC (coluna Quebra: dd/mm/aaaa)
    datas = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    try:
        col_data = _find_column(df, ["quebra", "data"])
        if _norm_name(col_data) != _norm_name(col_loja):
            datas = pd.to_datetime(df[col_data], dayfirst=True, errors="coerce")
    except KeyError:
        pass

    out = pd.DataFrame(
        {
            "data": datas,
            "bcps": df[col_loja].map(extract_bcps_from_venda),
            "loja_origem": df[col_loja].map(extract_loja_nome_from_venda),
            "codigo": df[col_cod].map(normalize_product_code),
            "descricao": df[col_desc].astype(str).str.strip(),
            "vendida": df[col_qtd].map(parse_br_number),
            "faturamento": df[col_fat].map(parse_br_number) if col_fat else 0.0,
            "tipo": tipo,
        }
    )
    return out.dropna(subset=["bcps", "codigo"])


def load_estoque(path: FileInput, tipo: str = "kit") -> pd.DataFrame:
    df = _read_csv(path)
    col_loja = _find_column(df, ["quebra 1", "quebra1", "loja"])
    col_cod = _find_column(df, ["codigo", "cod"])
    col_desc = _find_column(df, ["descricao", "desc"])
    col_est = _find_column(df, ["estoque", "saldo", "qtd"])
    try:
        col_venda = _find_column(df, ["venda", "preco venda", "preco de venda", "pv"])
    except KeyError:
        col_venda = None

    out = pd.DataFrame(
        {
            "bcps": df[col_loja].map(extract_bcps_from_estoque),
            "loja_origem": df[col_loja].map(extract_loja_nome_from_estoque),
            "codigo": df[col_cod].map(normalize_product_code),
            "descricao": df[col_desc].astype(str).str.strip(),
            "estoque": df[col_est].map(parse_br_number),
            "preco_venda": df[col_venda].map(parse_br_number) if col_venda else 0.0,
            "tipo": tipo,
        }
    )
    return out.dropna(subset=["bcps", "codigo"])


def load_dcentro(path: FileInput) -> pd.DataFrame:
    is_excel = False
    if hasattr(path, "name"):
        is_excel = str(getattr(path, "name", "")).lower().endswith((".xlsx", ".xlsm", ".xls"))
    elif isinstance(path, (str, Path)):
        is_excel = Path(path).suffix.lower() in {".xlsx", ".xlsm", ".xls"}

    if is_excel:
        df = pd.read_excel(path, sheet_name="dCentros", dtype=str)
        rename = {}
        for col in df.columns:
            low = _norm_name(col)
            if low == "bcps":
                rename[col] = "bcps"
            elif "pra" in low:
                rename[col] = "praca"
            elif "canal" in low:
                rename[col] = "canal"
            elif low == "loja":
                rename[col] = "loja_dc"
            elif low == "uf":
                rename[col] = "uf"
            elif "regional" in low:
                rename[col] = "regional"
            elif "cluster" in low:
                rename[col] = "cluster"
        df = df.rename(columns=rename)
    else:
        df = _read_csv(path)
        df = df.rename(
            columns={
                "BCPS": "bcps",
                "LOJA": "loja_dc",
                "PRACA": "praca",
                "CANAL": "canal",
                "UF": "uf",
                "REGIONAL": "regional",
                "CLUSTER": "cluster",
            }
        )

    keep = [c for c in ["bcps", "loja_dc", "praca", "canal", "uf", "regional", "cluster"] if c in df.columns]
    out = df[keep].copy()
    out["bcps"] = out["bcps"].map(normalize_product_code)
    return out.dropna(subset=["bcps"]).drop_duplicates(subset=["bcps"], keep="first")


def load_classificacao_produtos(path: Optional[FileInput]) -> Optional[pd.DataFrame]:
    """Optional CSV: codigo;tipo (kit | lancamento | promocionado)."""
    if path is None:
        return None
    if isinstance(path, (str, Path)) and not Path(path).exists():
        return None
    df = _read_csv(path)
    col_cod = _find_column(df, ["codigo", "cod"])
    col_tipo = _find_column(df, ["tipo", "categoria", "classe"])
    out = pd.DataFrame(
        {
            "codigo": df[col_cod].map(normalize_product_code),
            "tipo": df[col_tipo].astype(str).str.strip().str.lower(),
        }
    )
    return out.dropna(subset=["codigo"]).drop_duplicates(subset=["codigo"], keep="first")
