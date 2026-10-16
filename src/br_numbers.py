"""Parsing helpers for Brazilian number formats and store codes."""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd


def parse_br_number(value) -> float:
    """Parse numbers like '10,000' or '2.545,20' into floats."""
    if pd.isna(value):
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def normalize_product_code(value) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    text = text.lstrip("0")
    return text or "0"


def extract_bcps_from_venda(quebra2: str) -> Optional[str]:
    """'020836 - VD NORTE SHOPPING' -> '20836'."""
    match = re.match(r"(\d+)", str(quebra2).strip())
    if not match:
        return None
    return str(int(match.group(1)))


def extract_loja_nome_from_venda(quebra2: str) -> Optional[str]:
    text = str(quebra2).strip()
    if " - " in text:
        return text.split(" - ", 1)[1].strip()
    return text or None


def extract_bcps_from_estoque(quebra1: str) -> Optional[str]:
    """'Loja: 12488 - EXTREMOZ' -> '12488'."""
    match = re.search(r"Loja:\s*(\d+)", str(quebra1), flags=re.IGNORECASE)
    if not match:
        match = re.match(r"(\d+)", str(quebra1).strip())
    if not match:
        return None
    return str(int(match.group(1)))


def extract_loja_nome_from_estoque(quebra1: str) -> Optional[str]:
    text = str(quebra1).strip()
    cleaned = re.sub(r"^Loja:\s*\d+\s*-\s*", "", text, flags=re.IGNORECASE)
    return cleaned.strip() or None
