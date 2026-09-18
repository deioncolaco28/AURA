"""
Tests for XLSXAdapter: sheets, cell lookups, stats, and spreadsheet creation.
"""

from __future__ import annotations

from pathlib import Path
import openpyxl
import pytest

from app.content.adapters.xlsx_adapter import XLSXAdapter
from app.content.models import ContentType


def _create_sample_xlsx(path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "AirQuality"
    
    ws.append(["City", "AQI", "PM2_5"])
    ws.append(["Mumbai", 142, 58.2])
    ws.append(["Delhi", 280, 115.0])
    ws.append(["Bengaluru", 75, 24.5])
    
    wb.save(str(path))


class TestXLSXAdapter:
    def test_extract_xlsx_sheets_and_rows(self, tmp_path):
        xlsx_path = tmp_path / "data.xlsx"
        _create_sample_xlsx(xlsx_path)

        adapter = XLSXAdapter()
        doc = adapter.extract(str(xlsx_path))

        assert doc.source_type == ContentType.XLSX
        assert "AirQuality" in doc.sheet_names
        assert len(doc.sections) == 1
        assert "Mumbai | 142 | 58.2" in doc.full_text

    def test_search_xlsx_with_cell_coordinate_provenance(self, tmp_path):
        xlsx_path = tmp_path / "data.xlsx"
        _create_sample_xlsx(xlsx_path)

        adapter = XLSXAdapter()
        doc = adapter.extract(str(xlsx_path))

        results = adapter.search(doc, "Mumbai")
        assert len(results) == 1
        assert "AirQuality!A2" in results[0].location
        assert results[0].matched_text == "Mumbai"

    def test_analyze_sheet_statistics(self, tmp_path):
        xlsx_path = tmp_path / "data.xlsx"
        _create_sample_xlsx(xlsx_path)

        adapter = XLSXAdapter()
        stats = adapter.analyze_sheet(str(xlsx_path))

        assert stats["record_count"] == 3
        assert "AQI" in stats["numeric_columns"]
        assert stats["numeric_columns"]["AQI"]["min"] == 75
        assert stats["numeric_columns"]["AQI"]["max"] == 280

    def test_create_spreadsheet(self, tmp_path):
        out_path = tmp_path / "summary.xlsx"
        adapter = XLSXAdapter()
        
        created = adapter.create_spreadsheet(
            output_path=out_path,
            headers=["Name", "Score"],
            rows=[["Alice", 95], ["Bob", 88]],
        )

        assert Path(created).exists()
        doc = adapter.extract(created)
        assert "Alice | 95" in doc.full_text
