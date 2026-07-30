"""
Streamlit Safe Rendering Helpers — Learnova
============================================
Centralises every Streamlit data-rendering call so that raw Python objects
(nested dicts, dataclasses, bytes, enums, numpy scalars …) are never passed
directly to st.dataframe() / pyarrow, which causes a Fatal Segmentation Fault
on macOS with PyArrow + Python 3.12.

Public API
----------
safe_dataframe(data, columns=None, **kwargs)
    Render a list-of-dicts or list-of-lists as a Streamlit dataframe, fully
    sanitised so PyArrow never receives a non-primitive value.

safe_json(data, **kwargs)
    Render any Python object as collapsed, pretty JSON (st.json).

safe_display(data, label="", **kwargs)
    Auto-detect best renderer: table-like → safe_dataframe, dict/list → safe_json,
    else st.write.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
import streamlit as st

logger = logging.getLogger("learnova")

# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

_PRIMITIVES = (str, int, float, bool, type(None))


def _to_primitive(val: Any) -> Any:
    """
    Recursively convert a value to a type that PyArrow can safely serialise:
      - str / int / float / bool / None  → unchanged
      - bytes                            → "<bytes>"
      - list / tuple / set              → JSON string
      - dict                            → JSON string
      - anything else                   → str(val)
    """
    if isinstance(val, _PRIMITIVES):
        return val
    if isinstance(val, bytes):
        return "<bytes>"
    if isinstance(val, (list, tuple, set)):
        try:
            return json.dumps(list(val), ensure_ascii=False)
        except Exception:
            return str(val)
    if isinstance(val, dict):
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    # numpy scalars, enums, dataclasses, custom objects …
    try:
        # numpy scalar → Python native
        return val.item()  # type: ignore[attr-defined]
    except Exception:
        pass
    return str(val)


def _sanitise_row(row: Any) -> list:
    """Convert a row (list/tuple) to a list of safe primitives."""
    if isinstance(row, (list, tuple)):
        return [_to_primitive(cell) for cell in row]
    # Scalar row — wrap in a single-element list
    return [_to_primitive(row)]


def _sanitise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with every object-dtype column cast to str."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(_to_primitive)
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def safe_dataframe(
    data: Any,
    columns: list[str] | None = None,
    **kwargs,
) -> None:
    """
    Safely render tabular data as a Streamlit dataframe.

    Parameters
    ----------
    data : list[list] | list[dict] | pd.DataFrame | dict
        The data to render.
    columns : list[str] | None
        Column names (only used when `data` is a list-of-lists).
    **kwargs
        Forwarded to st.dataframe().
    """
    try:
        if isinstance(data, pd.DataFrame):
            df = _sanitise_dataframe(data)

        elif isinstance(data, list):
            if not data:
                st.info("*(No data to display)*")
                return

            first = data[0]
            if isinstance(first, dict):
                # list-of-dicts: sanitise each value
                safe_rows = [
                    {k: _to_primitive(v) for k, v in row.items()}
                    for row in data
                ]
                df = pd.DataFrame(safe_rows)
            else:
                # list-of-lists / list-of-scalars
                safe_rows = [_sanitise_row(row) for row in data]
                df = pd.DataFrame(safe_rows, columns=columns)

        elif isinstance(data, dict):
            safe_rows = [
                {"Key": _to_primitive(k), "Value": _to_primitive(v)}
                for k, v in data.items()
            ]
            df = pd.DataFrame(safe_rows)

        else:
            # Fallback: just write the repr
            st.write(data)
            return

        # Final safety net: cast every object column to str
        df = _sanitise_dataframe(df)
        st.dataframe(df, **kwargs)

    except Exception as exc:
        logger.error("safe_dataframe rendering failed: %s", exc, exc_info=True)
        # Last-resort: dump as JSON
        try:
            if isinstance(data, pd.DataFrame):
                st.json(data.to_dict(orient="records"))
            else:
                st.json(data)
        except Exception:
            st.write(str(data))


def safe_json(data: Any, **kwargs) -> None:
    """
    Render any Python object as Streamlit JSON, with a str fallback.
    """
    try:
        # Make sure the object is JSON-serialisable
        json.dumps(data, default=str)
        st.json(data, **kwargs)
    except Exception as exc:
        logger.warning("safe_json serialisation failed: %s", exc)
        st.write(str(data))


def safe_display(data: Any, label: str = "", **kwargs) -> None:
    """
    Auto-select the best Streamlit renderer for `data`:
      - pd.DataFrame or list-of-lists/dicts → safe_dataframe
      - dict / list-of-scalars              → safe_json
      - everything else                      → st.write
    """
    if label:
        st.markdown(f"**{label}**")

    if isinstance(data, pd.DataFrame):
        safe_dataframe(data, **kwargs)
        return

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, (list, tuple, dict)):
            safe_dataframe(data, **kwargs)
            return
        # list of scalars → JSON array
        safe_json(data, **kwargs)
        return

    if isinstance(data, dict):
        safe_json(data, **kwargs)
        return

    st.write(data)
