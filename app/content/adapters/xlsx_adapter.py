"""
app/content/adapters/xlsx_adapter.py

XLSX spreadsheet extraction, search, statistics, and generation adapter for AURA using openpyxl.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl

from app.content.adapters.base import BaseContentAdapter
from app.content.models import (
    BlockType,
    ContentBlock,
    ContentDocument,
    ContentSearchResult,
    ContentSection,
    ContentType,
)


class XLSXAdapter(BaseContentAdapter):
    """Extracts, indexes, searches, analyzes, and creates Excel (.xlsx) workbooks."""

    def extract(self, source_path_or_url: str) -> ContentDocument:
        """Extract sheets, rows, and cells from an XLSX file."""
        path = Path(source_path_or_url).resolve()
        if not path.exists():
            raise FileNotFoundError(f"XLSX file not found: '{path}'")

        try:
            wb = openpyxl.load_workbook(str(path), data_only=True)
        except Exception as e:
            raise RuntimeError(f"Failed to open XLSX '{path}': {e}")

        sections: list[ContentSection] = []

        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            rows_data: list[list[str]] = []
            max_row = ws.max_row or 0
            max_col = ws.max_column or 0

            for row in ws.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    row_str = [str(cell).strip() if cell is not None else "" for cell in row]
                    rows_data.append(row_str)

            table_text = "\n".join(" | ".join(r) for r in rows_data)

            sections.append(
                ContentSection(
                    title=f"Sheet: {sheetname}",
                    location=f"Sheet: {sheetname}",
                    blocks=[
                        ContentBlock(
                            block_type=BlockType.CELL_RANGE,
                            text=table_text,
                            metadata={"max_row": max_row, "max_col": max_col, "rows": rows_data},
                        )
                    ],
                    raw_text=table_text,
                    metadata={"sheet_name": sheetname, "row_count": len(rows_data)},
                )
            )

        return ContentDocument(
            title=path.stem,
            source_type=ContentType.XLSX,
            source_path=str(path),
            sections=sections,
            sheet_names=list(wb.sheetnames),
            metadata={"sheet_count": len(wb.sheetnames)},
        )

    def search(self, document: ContentDocument, query: str) -> list[ContentSearchResult]:
        """Search cells in XLSX with exact Sheet!Coordinate provenance."""
        results: list[ContentSearchResult] = []
        path = Path(document.source_path)
        if not path.exists():
            return super().search(document, query)

        try:
            wb = openpyxl.load_workbook(str(path), data_only=True)
            q_clean = query.strip().lower()

            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.value is not None:
                            val_str = str(cell.value)
                            if q_clean in val_str.lower():
                                coord = f"{sheetname}!{cell.coordinate}"
                                results.append(
                                    ContentSearchResult(
                                        query=query,
                                        document_path=str(path),
                                        location=coord,
                                        matched_text=val_str,
                                        context=f"Cell {coord}: {val_str}",
                                        confidence=1.0,
                                    )
                                )
        except Exception:
            return super().search(document, query)

        return results

    def analyze_sheet(
        self,
        source_path: str,
        sheet_name: str | None = None,
        column: str | int | None = None,
    ) -> dict[str, Any]:
        """Compute summary statistics for numeric data or count records."""
        path = Path(source_path).resolve()
        wb = openpyxl.load_workbook(str(path), data_only=True)
        ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

        data_rows = list(ws.iter_rows(values_only=True))
        if not data_rows:
            return {"record_count": 0, "headers": []}

        headers = [str(h or f"Col_{idx}") for idx, h in enumerate(data_rows[0], start=1)]
        records = data_rows[1:]

        stats: dict[str, Any] = {
            "sheet_name": ws.title,
            "record_count": len(records),
            "headers": headers,
            "numeric_columns": {},
        }

        # Find numeric column stats
        for col_idx, header in enumerate(headers):
            col_vals = []
            for r in records:
                if col_idx < len(r) and r[col_idx] is not None:
                    try:
                        col_vals.append(float(r[col_idx]))
                    except (ValueError, TypeError):
                        pass

            if col_vals:
                stats["numeric_columns"][header] = {
                    "count": len(col_vals),
                    "min": min(col_vals),
                    "max": max(col_vals),
                    "sum": sum(col_vals),
                    "average": sum(col_vals) / len(col_vals),
                }

        return stats

    def create_spreadsheet(
        self,
        output_path: str | Path,
        headers: list[str],
        rows: list[list[Any]],
        sheet_name: str = "Data",
    ) -> str:
        """Create a new formatted XLSX file."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        if headers:
            ws.append(headers)
        for r in rows:
            ws.append(r)

        wb.save(str(target))
        return str(target)
