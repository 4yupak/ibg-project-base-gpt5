"""
PDF price parser.
Uses multiple methods: pdfplumber, tabula-py, camelot, with LLM fallback.
"""
import os
import time
import logging
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path

import pdfplumber
import pandas as pd

from .base import (
    BasePriceParser, ParsedUnit, ParsedPriceData, ParsingResult, UnitStatus
)

logger = logging.getLogger(__name__)


class PDFPriceParser(BasePriceParser):
    """Parser for PDF files with tables."""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is PDF."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    async def parse(self, file_path: str, **kwargs) -> ParsingResult:
        """
        Parse PDF file.
        
        Tries methods in order:
        1. pdfplumber (best for simple tables)
        2. tabula-py (Java-based, good accuracy)
        3. LLM fallback (for complex/non-standard PDFs)
        
        Keyword args:
            pages: str - Pages to parse (default: 'all')
            force_llm: bool - Skip table extraction, go straight to LLM
            project_id: int - For LLM context
        """
        start_time = time.time()
        result = ParsingResult(parsing_method='pdf')
        
        force_llm = kwargs.get('force_llm', False)
        
        if not force_llm:
            # Try pdfplumber first
            result = await self._parse_with_pdfplumber(file_path, **kwargs)
            
            if result.success and result.data and result.data.valid_count > 0:
                result.parsing_time_ms = int((time.time() - start_time) * 1000)
                return result
            
            # Try tabula if pdfplumber failed or found no data
            logger.info("pdfplumber failed or no data, trying tabula...")
            result = await self._parse_with_tabula(file_path, **kwargs)
            
            if result.success and result.data and result.data.valid_count > 0:
                result.parsing_method = 'tabula'
                result.parsing_time_ms = int((time.time() - start_time) * 1000)
                return result
        
        # Fallback to LLM
        logger.info("Table extraction failed, would use LLM fallback")
        result.success = False
        result.error_message = "Table extraction failed. LLM fallback needed."
        result.error_type = "TableExtractionFailed"
        result.fallback_used = True
        result.parsing_time_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    async def _parse_with_pdfplumber(self, file_path: str, **kwargs) -> ParsingResult:
        """Parse PDF using pdfplumber."""
        result = ParsingResult(parsing_method='pdfplumber')
        
        try:
            pages = kwargs.get('pages', 'all')
            all_tables = []
            
            with pdfplumber.open(file_path) as pdf:
                # Determine which pages to process
                if pages == 'all':
                    page_list = pdf.pages
                elif isinstance(pages, str):
                    # Parse page range like "1-5" or "1,3,5"
                    page_list = self._parse_page_range(pages, len(pdf.pages), pdf)
                else:
                    page_list = [pdf.pages[i-1] for i in pages if i <= len(pdf.pages)]
                
                for page in page_list:
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:  # At least header + 1 row
                            all_tables.append(table)
            
            if not all_tables:
                result.success = False
                result.error_message = "No tables found in PDF"
                result.error_type = "NoTablesFound"
                return result
            
            # Convert tables to DataFrame and parse
            parsed_data = self._process_tables(all_tables, **kwargs)
            
            result.success = True
            result.data = parsed_data
            
            if parsed_data.invalid_count > 0:
                result.warnings.append(
                    f"{parsed_data.invalid_count} units had validation errors"
                )
            
            logger.info(f"pdfplumber parsed {parsed_data.valid_count} valid units")
            
        except Exception as e:
            logger.error(f"pdfplumber parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        return result
    
    async def _parse_with_tabula(self, file_path: str, **kwargs) -> ParsingResult:
        """Parse PDF using tabula-py."""
        result = ParsingResult(parsing_method='tabula')
        
        try:
            import tabula
            
            pages = kwargs.get('pages', 'all')
            
            # Extract tables with tabula
            tables = tabula.read_pdf(
                file_path,
                pages=pages,
                multiple_tables=True,
                pandas_options={'header': None}
            )
            
            if not tables:
                result.success = False
                result.error_message = "No tables found with tabula"
                result.error_type = "NoTablesFound"
                return result
            
            # Convert to list format for processing
            all_tables = []
            for df in tables:
                if not df.empty:
                    table = df.values.tolist()
                    # Add headers from first row
                    headers = df.iloc[0].tolist() if len(df) > 0 else []
                    all_tables.append([headers] + table[1:] if len(table) > 1 else table)
            
            # Process tables
            parsed_data = self._process_tables(all_tables, **kwargs)
            
            result.success = True
            result.data = parsed_data
            
            logger.info(f"tabula parsed {parsed_data.valid_count} valid units")
            
        except ImportError:
            logger.warning("tabula-py not installed")
            result.success = False
            result.error_message = "tabula-py not installed"
            result.error_type = "DependencyMissing"
        except Exception as e:
            logger.error(f"tabula parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        return result
    
    def _parse_page_range(self, pages: str, total_pages: int, pdf) -> List:
        """Parse page range string like '1-5' or '1,3,5' into page objects."""
        result = []
        
        for part in pages.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), min(int(end) + 1, total_pages + 1)):
                    if i <= total_pages:
                        result.append(pdf.pages[i - 1])
            else:
                i = int(part)
                if i <= total_pages:
                    result.append(pdf.pages[i - 1])
        
        return result
    
    def _process_tables(self, tables: List[List[List]], **kwargs) -> ParsedPriceData:
        """Process extracted tables into ParsedPriceData."""
        result = ParsedPriceData()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # First row is header
            headers = [str(h).strip() if h else '' for h in table[0]]
            result.raw_headers.extend(headers)
            
            # Detect column mappings
            col_mapping = self.detect_columns(headers)
            
            if not col_mapping:
                # No recognizable columns, skip this table
                continue
            
            # Detect currency from headers
            header_text = ' '.join(headers)
            currency = kwargs.get('currency') or self.detect_currency(header_text)
            result.currency = currency
            
            # Parse rows
            for row in table[1:]:
                if not row or all(not cell for cell in row):
                    continue
                
                raw_row = dict(zip(headers, row))
                result.raw_data.append(raw_row)
                
                unit = self._parse_table_row(row, col_mapping, currency)
                if unit:
                    unit.raw_row = raw_row
                    result.units.append(unit)
        
        return result
    
    def _parse_table_row(
        self, 
        row: List, 
        col_mapping: Dict[str, int],
        currency: str
    ) -> Optional[ParsedUnit]:
        """Parse a single table row into ParsedUnit."""
        
        # Get unit number
        unit_number = None
        if 'unit_number' in col_mapping:
            idx = col_mapping['unit_number']
            if idx < len(row) and row[idx]:
                unit_number = str(row[idx]).strip()
        
        if not unit_number or unit_number.lower() in ['nan', 'none', '', 'unit']:
            return None
        
        unit = ParsedUnit(unit_number=unit_number, currency=currency)
        
        # Parse other fields
        def safe_get(field: str):
            if field in col_mapping and col_mapping[field] < len(row):
                return row[col_mapping[field]]
            return None
        
        # Bedrooms
        value = safe_get('bedrooms')
        if value:
            unit.bedrooms = self.parse_bedrooms(value)
        
        # Area
        value = safe_get('area')
        if value:
            unit.area_sqm = self.parse_area(value)
        
        # Floor
        value = safe_get('floor')
        if value:
            unit.floor = self.parse_floor(value)
        
        # Price
        value = safe_get('price')
        if value:
            unit.price = self.parse_price(value)
            if unit.price and unit.area_sqm:
                unit.price_per_sqm = round(unit.price / unit.area_sqm, 2)
        
        # Status
        value = safe_get('status')
        if value:
            unit.status = ParsedUnit._parse_status(str(value))
        
        # View
        value = safe_get('view')
        if value:
            unit.view_type = str(value).strip()
        
        # Building
        value = safe_get('building')
        if value:
            unit.building = str(value).strip()
        
        # Layout
        value = safe_get('layout')
        if value:
            unit.layout_type = str(value).strip()
            if unit.bedrooms is None:
                unit.bedrooms = ParsedUnit._extract_bedrooms_from_layout(unit.layout_type)
        
        # Phase
        value = safe_get('phase')
        if value:
            unit.phase = str(value).strip()
        
        unit._validate()
        return unit
    
    def extract_text(self, file_path: str) -> str:
        """Extract all text from PDF (for LLM fallback)."""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return '\n\n'.join(text_parts)
