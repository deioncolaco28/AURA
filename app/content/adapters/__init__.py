"""
app/content/adapters package
"""

from app.content.adapters.base import BaseContentAdapter
from app.content.adapters.docx_adapter import DOCXAdapter
from app.content.adapters.pdf_adapter import PDFAdapter
from app.content.adapters.pptx_adapter import PPTXAdapter
from app.content.adapters.web_adapter import WebContentAdapter
from app.content.adapters.xlsx_adapter import XLSXAdapter

__all__ = [
    "BaseContentAdapter",
    "PDFAdapter",
    "DOCXAdapter",
    "XLSXAdapter",
    "PPTXAdapter",
    "WebContentAdapter",
]
