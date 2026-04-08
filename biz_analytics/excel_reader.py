"""
Excel multi-sheet reader for the Harvard Business Analytics Framework.

Reads an Excel file (all sheets or selected sheets), extracts:
- Column names and types
- Row counts and completeness
- Numeric statistics (min/max/mean/nulls)
- Sample rows (first 5)

The result is a compact text summary that gets injected into the
analysis prompt so the LLM can reason about actual data structure.

Dependencies: pip install pandas openpyxl
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class ColumnStat:
    name: str
    dtype: str
    non_null: int
    null_count: int
    unique_count: int
    sample_values: list         # up to 5 unique non-null values
    min_val: Optional[float | str] = None
    max_val: Optional[float | str] = None
    mean_val: Optional[float] = None


@dataclass
class SheetSummary:
    sheet_name: str
    row_count: int
    col_count: int
    columns: list[ColumnStat] = field(default_factory=list)
    sample_rows: list[dict] = field(default_factory=list)   # first 5 rows as dicts
    notes: list[str] = field(default_factory=list)          # warnings (empty cols, etc.)


@dataclass
class ExcelSummary:
    file_path: str
    sheet_names: list[str]
    sheets: list[SheetSummary] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return sum(s.row_count for s in self.sheets)

    @property
    def total_cols(self) -> int:
        return sum(s.col_count for s in self.sheets)


# ── Core reading logic ────────────────────────────────────────────────────────

def _analyze_column(series: pd.Series) -> ColumnStat:
    """Compute statistics for a single DataFrame column."""
    non_null = series.notna().sum()
    null_count = series.isna().sum()
    unique_vals = series.dropna().unique()
    sample = [str(v) for v in unique_vals[:5]]

    stat = ColumnStat(
        name=str(series.name),
        dtype=str(series.dtype),
        non_null=int(non_null),
        null_count=int(null_count),
        unique_count=int(len(unique_vals)),
        sample_values=sample,
    )

    # Numeric stats
    if pd.api.types.is_numeric_dtype(series):
        clean = series.dropna()
        if len(clean) > 0:
            stat.min_val = round(float(clean.min()), 4)
            stat.max_val = round(float(clean.max()), 4)
            stat.mean_val = round(float(clean.mean()), 4)

    # Date range
    elif pd.api.types.is_datetime64_any_dtype(series):
        clean = series.dropna()
        if len(clean) > 0:
            stat.min_val = str(clean.min().date())
            stat.max_val = str(clean.max().date())

    return stat


def _analyze_sheet(name: str, df: pd.DataFrame, max_sample_rows: int = 5) -> SheetSummary:
    """Summarize a single sheet DataFrame."""
    # Try to infer datetime columns
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_datetime(df[col], infer_datetime_format=True)
            except (ValueError, TypeError):
                pass

    columns = [_analyze_column(df[col]) for col in df.columns]

    # Sample rows (convert to plain dicts with string values)
    sample_rows = []
    for _, row in df.head(max_sample_rows).iterrows():
        sample_rows.append({str(k): str(v) for k, v in row.items()})

    notes = []
    fully_empty = [c.name for c in columns if c.non_null == 0]
    if fully_empty:
        notes.append(f"Fully empty columns: {fully_empty}")
    high_null = [c.name for c in columns if c.null_count > 0 and c.null_count / max(len(df), 1) > 0.5]
    if high_null:
        notes.append(f"Columns with >50% missing values: {high_null}")

    return SheetSummary(
        sheet_name=name,
        row_count=len(df),
        col_count=len(df.columns),
        columns=columns,
        sample_rows=sample_rows,
        notes=notes,
    )


def read_excel(
    path: str | Path,
    sheets: list[str] | None = None,
    max_rows_per_sheet: int | None = None,
) -> ExcelSummary:
    """
    Read an Excel file and return a structured summary of all (or selected) sheets.

    Args:
        path:               Path to the .xlsx / .xls file.
        sheets:             Sheet names to read. None = read all sheets.
        max_rows_per_sheet: If set, only read the first N rows per sheet.

    Returns:
        ExcelSummary with per-sheet column stats and sample rows.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if requested sheets are not found in the file.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    if path.suffix.lower() not in {".xlsx", ".xls", ".xlsm", ".xlsb"}:
        raise ValueError(f"Unsupported file type: {path.suffix}. Use .xlsx or .xls.")

    xl = pd.ExcelFile(path)
    available = xl.sheet_names

    if sheets is not None:
        missing = [s for s in sheets if s not in available]
        if missing:
            raise ValueError(
                f"Sheets not found in {path.name}: {missing}. "
                f"Available sheets: {available}"
            )
        target_sheets = sheets
    else:
        target_sheets = available

    summary = ExcelSummary(file_path=str(path), sheet_names=available)

    for sheet_name in target_sheets:
        nrows = max_rows_per_sheet  # None means all rows
        df = xl.parse(sheet_name, nrows=nrows)
        summary.sheets.append(_analyze_sheet(sheet_name, df))

    return summary


# ── Text rendering (injected into LLM prompt) ────────────────────────────────

def summary_to_text(summary: ExcelSummary, max_sample_rows: int = 3) -> str:
    """
    Convert an ExcelSummary to a compact text block for use in LLM prompts.
    Keeps it concise to avoid blowing up the context window.
    """
    lines = [
        f"Excel File: {Path(summary.file_path).name}",
        f"Total sheets: {len(summary.sheets)} | "
        f"Total rows: {summary.total_rows} | "
        f"Total columns: {summary.total_cols}",
        "",
    ]

    for sheet in summary.sheets:
        lines.append(f"--- Sheet: '{sheet.sheet_name}' "
                     f"({sheet.row_count} rows × {sheet.col_count} cols) ---")

        if sheet.notes:
            for note in sheet.notes:
                lines.append(f"  ⚠ {note}")

        # Column overview
        lines.append("  Columns:")
        for col in sheet.columns:
            null_pct = round(col.null_count / max(sheet.row_count, 1) * 100, 1)
            stat_str = ""
            if col.mean_val is not None:
                stat_str = f" | range [{col.min_val} – {col.max_val}], mean={col.mean_val}"
            elif col.min_val is not None:
                stat_str = f" | range [{col.min_val} – {col.max_val}]"
            lines.append(
                f"    • {col.name} ({col.dtype}): "
                f"{col.unique_count} unique, {null_pct}% null"
                f"{stat_str}"
            )
            if col.sample_values:
                lines.append(f"      samples: {', '.join(col.sample_values[:3])}")

        # Sample rows
        if sheet.sample_rows:
            lines.append(f"  First {min(max_sample_rows, len(sheet.sample_rows))} rows:")
            for row in sheet.sample_rows[:max_sample_rows]:
                lines.append(f"    {row}")

        lines.append("")

    return "\n".join(lines)
