"""
Streamlit Safe Rendering Helpers — Learnova
============================================
ALL table rendering goes through _render_html_table() which builds a plain
HTML <table> and emits it via st.markdown(unsafe_allow_html=True).

This completely eliminates the PyArrow / Arrow serialisation code path.
st.dataframe() is NEVER called — it causes a Fatal Segmentation Fault
on macOS + Python 3.12 + PyArrow when object-dtype columns contain values
that PyArrow cannot safely convert (nested dicts, LLM-generated rows, etc.)

Public API
----------
safe_dataframe(data, columns=None, label="", **_)
    Render any tabular data as a zero-Arrow HTML table.

safe_json(data, **kwargs)
    Render any Python object as pretty JSON (st.json).

safe_display(data, label="", **kwargs)
    Auto-detect best renderer.
"""

from __future__ import annotations

import html
import json
import logging
from typing import Any

import pandas as pd
import streamlit as st

logger = logging.getLogger("learnova")

# ---------------------------------------------------------------------------
# Primitive conversion — makes every value HTML-safe and PyArrow-free
# ---------------------------------------------------------------------------

_PRIMITIVES = (str, int, float, bool, type(None))


def _to_primitive(val: Any) -> Any:
    """
    Recursively convert a value to a type safe for display:
      str / int / float / bool / None  → unchanged
      bytes                            → "<bytes>"
      list / tuple / set               → JSON string
      dict                             → JSON string
      numpy scalar                     → Python native via .item()
      everything else                  → str(val)
    """
    if isinstance(val, _PRIMITIVES):
        return val
    if isinstance(val, bytes):
        return "<bytes>"
    if isinstance(val, (list, tuple, set)):
        try:
            return json.dumps(list(val), ensure_ascii=False, default=str)
        except Exception:
            return str(val)
    if isinstance(val, dict):
        try:
            return json.dumps(val, ensure_ascii=False, default=str)
        except Exception:
            return str(val)
    # numpy scalars, enums, dataclasses, custom objects
    try:
        return val.item()  # type: ignore[attr-defined]
    except Exception:
        pass
    return str(val)


def _sanitise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with every object-dtype column cast via _to_primitive."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(_to_primitive)
    return df


# ---------------------------------------------------------------------------
# Core HTML table renderer — ZERO PyArrow involvement
# ---------------------------------------------------------------------------

_TABLE_CSS = """
<style>
.lr-table-wrap { overflow-x: auto; margin: 8px 0; }
.lr-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    background: #ffffff;
}
.lr-table th {
    background: #1e2761;
    color: #ccff00;
    font-weight: 700;
    padding: 9px 14px;
    text-align: left;
    border: 1px solid #000;
    white-space: nowrap;
}
.lr-table td {
    padding: 7px 14px;
    border: 1px solid #d0d0d0;
    color: #222;
    vertical-align: top;
    word-break: break-word;
    max-width: 420px;
}
.lr-table tr:nth-child(even) td { background: #f7f7f7; }
.lr-table tr:hover td { background: #fffde7; }
</style>
"""

_TABLE_CSS_INJECTED = False  # inject once per Streamlit session render


def _render_html_table(
    headers: list[str],
    rows: list[list],
    label: str = "",
) -> None:
    """
    Render tabular data as a styled HTML table via st.markdown().
    No pandas, no PyArrow, no st.dataframe() — zero chance of segfault.
    """
    global _TABLE_CSS_INJECTED
    if not _TABLE_CSS_INJECTED:
        st.markdown(_TABLE_CSS, unsafe_allow_html=True)
        _TABLE_CSS_INJECTED = True

    if label:
        st.markdown(f"**{label}**")

    # ── Logging ──────────────────────────────────────────────────────────────
    logger.info(
        "Rendering HTML table %r — %d cols × %d rows — cols=%s",
        label or "<unnamed>",
        len(headers),
        len(rows),
        headers,
    )

    # ── Build HTML ───────────────────────────────────────────────────────────
    parts: list[str] = ['<div class="lr-table-wrap"><table class="lr-table">']

    # Header row
    parts.append("<thead><tr>")
    for h in headers:
        parts.append(f"<th>{html.escape(str(h))}</th>")
    parts.append("</tr></thead>")

    # Data rows
    parts.append("<tbody>")
    for row in rows:
        parts.append("<tr>")
        for cell in row:
            p = _to_primitive(cell)
            cell_str = "" if p is None else str(p)
            parts.append(f"<td>{html.escape(cell_str)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")

    st.markdown("".join(parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def safe_dataframe(
    data: Any,
    columns: list[str] | None = None,
    label: str = "",
    **_,          # absorb use_container_width and any other kwargs harmlessly
) -> None:
    """
    Safely render tabular data — NEVER calls st.dataframe() or PyArrow.

    Parameters
    ----------
    data : list[list] | list[dict] | pd.DataFrame | dict
    columns : list[str] | None
        Column names (used when data is a list-of-lists).
    label : str
        Optional heading printed above the table.
    """
    try:
        if not data and not isinstance(data, pd.DataFrame):
            st.info("*(No data to display)*")
            return

        # ── Normalise to (headers, rows) ──────────────────────────────────
        if isinstance(data, pd.DataFrame):
            df = _sanitise_dataframe(data)
            headers = [str(c) for c in df.columns]
            rows = [
                [_to_primitive(cell) for cell in record]
                for record in df.itertuples(index=False, name=None)
            ]

        elif isinstance(data, list):
            if not data:
                st.info("*(No data to display)*")
                return

            first = data[0]
            if isinstance(first, dict):
                # list-of-dicts
                if columns:
                    headers = [str(c) for c in columns]
                else:
                    # union of all keys in insertion order
                    seen_keys: dict[str, None] = {}
                    for row_d in data:
                        if isinstance(row_d, dict):
                            for k in row_d:
                                seen_keys[str(k)] = None
                    headers = list(seen_keys)
                rows = [
                    [_to_primitive(row_d.get(h)) for h in headers]
                    if isinstance(row_d, dict)
                    else [_to_primitive(row_d)]
                    for row_d in data
                ]

            elif isinstance(first, (list, tuple)):
                # list-of-lists
                headers = [str(c) for c in columns] if columns else [
                    f"Col {i+1}" for i in range(len(first))
                ]
                rows = [
                    [_to_primitive(cell) for cell in row]
                    for row in data
                ]

            else:
                # list of scalars — single-column
                headers = [str(columns[0])] if columns else ["Value"]
                rows = [[_to_primitive(v)] for v in data]

        elif isinstance(data, dict):
            headers = ["Key", "Value"]
            rows = [
                [_to_primitive(k), _to_primitive(v)]
                for k, v in data.items()
            ]

        else:
            st.write(data)
            return

        _render_html_table(headers, rows, label=label)

    except Exception as exc:
        logger.error("safe_dataframe rendering failed: %s", exc, exc_info=True)
        # Absolute last resort — plain text
        try:
            st.json(
                data.to_dict(orient="records")
                if isinstance(data, pd.DataFrame)
                else data
            )
        except Exception:
            st.write(str(data))


def safe_json(data: Any, **kwargs) -> None:
    """
    Render any Python object as Streamlit JSON, with a str fallback.
    """
    try:
        json.dumps(data, default=str)
        st.json(data, **kwargs)
    except Exception as exc:
        logger.warning("safe_json serialisation failed: %s", exc)
        st.write(str(data))


def safe_display(data: Any, label: str = "", **kwargs) -> None:
    """
    Auto-select best Streamlit renderer:
      DataFrame or list-of-lists/dicts  → safe_dataframe (HTML table)
      dict / list-of-scalars            → safe_json
      everything else                   → st.write
    """
    if isinstance(data, pd.DataFrame):
        safe_dataframe(data, label=label, **kwargs)
        return

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, (list, tuple, dict)):
            safe_dataframe(data, label=label, **kwargs)
            return
        safe_json(data, **kwargs)
        return

    if isinstance(data, dict):
        safe_json(data, **kwargs)
        return

    st.write(data)
