"""
Excel/CSV price parser.
Supports: .xlsx, .xls, .csv
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
import openpyxl

from .base import (
    BasePriceParser, ParsedUnit, ParsedPriceData, ParsingResult, UnitStatus
)

logger = logging.getLogger(__name__)


class ExcelPriceParser(BasePriceParser):
    """Parser for Excel and CSV files."""
    
    SUPPORTED_EXTENSIONS = ['.xlsx', '.xls', '.csv']
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is Excel or CSV."""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    async def parse(self, file_path: str, **kwargs) -> ParsingResult:
        """
        Parse Excel/CSV file.
        
        Keyword args:
            sheet_name: str - Name of sheet to parse (default: first sheet)
            header_row: int - Row number for headers (default: auto-detect)
            skip_rows: int - Number of rows to skip at top
            currency: str - Force currency (default: auto-detect)
        """
        start_time = time.time()
        result = ParsingResult(parsing_method='excel')
        
        try:
            # Read file into DataFrame
            ext = Path(file_path).suffix.lower()
            sheet_name = kwargs.get('sheet_name', 0)
            header_row = kwargs.get('header_row')
            
            if ext == '.csv':
                # Try different encodings
                for encoding in ['utf-8', 'cp1251', 'latin-1']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Could not decode CSV file with any encoding")
            else:
                df = pd.read_excel(
                    file_path, 
                    sheet_name=sheet_name,
                    header=header_row
                )
            
            # Auto-detect header row if not specified
            if header_row is None:
                df, detected_row = self._auto_detect_header(df)
                if detected_row > 0:
                    result.warnings.append(f"Auto-detected header at row {detected_row}")
            
            # Parse the data
            parsed_data = self._parse_dataframe(df, **kwargs)
            
            result.success = True
            result.data = parsed_data
            result.parsing_time_ms = int((time.time() - start_time) * 1000)
            
            if parsed_data.invalid_count > 0:
                result.warnings.append(
                    f"{parsed_data.invalid_count} units had validation errors"
                )
            
            logger.info(
                f"Excel parsing complete: {parsed_data.valid_count} valid units, "
                f"{parsed_data.invalid_count} invalid"
            )
            
        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.parsing_time_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    def _auto_detect_header(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """
        Auto-detect header row by finding row with most recognized column names.
        Returns (new_dataframe, header_row_index).
        """
        # Flatten all column mapping keywords
        all_keywords = set()
        for keywords in self.COLUMN_MAPPINGS.values():
            all_keywords.update(keywords)
        
        best_row = 0
        best_match_count = 0
        
        # Check first 10 rows
        for i in range(min(10, len(df))):
            row_values = df.iloc[i].astype(str).str.lower().str.strip().tolist()
            match_count = sum(1 for v in row_values if v in all_keywords or any(k in v for k in all_keywords))
            
            if match_count > best_match_count:
                best_match_count = match_count
                best_row = i
        
        # If header is not in first row, re-read with correct header
        if best_row > 0 and best_match_count >= 3:
            # Set new headers and skip rows before
            new_headers = df.iloc[best_row].astype(str).tolist()
            df = df.iloc[best_row + 1:].reset_index(drop=True)
            df.columns = new_headers
        
        # Also check if current columns look like headers
        current_cols = [str(c).lower().strip() for c in df.columns]
        current_match = sum(1 for c in current_cols if c in all_keywords or any(k in c for k in all_keywords))
        
        if current_match >= 3:
            best_row = 0
        
        return df, best_row
    
    def _parse_dataframe(self, df: pd.DataFrame, **kwargs) -> ParsedPriceData:
        """Parse DataFrame into ParsedPriceData."""
        result = ParsedPriceData()
        
        # Store raw headers
        result.raw_headers = [str(c) for c in df.columns]
        
        # Detect column mappings
        col_mapping = self.detect_columns(result.raw_headers)
        logger.debug(f"Detected column mapping: {col_mapping}")
        
        # Detect currency from headers or first few rows
        currency = kwargs.get('currency')
        if not currency:
            header_text = ' '.join(result.raw_headers)
            first_rows_text = ' '.join(df.head(5).astype(str).values.flatten())
            currency = self.detect_currency(header_text + ' ' + first_rows_text)
        result.currency = currency
        
        # Parse each row
        for idx, row in df.iterrows():
            # Skip empty rows
            if row.isna().all():
                continue
            
            # Store raw row data
            raw_row = row.to_dict()
            result.raw_data.append(raw_row)
            
            # Try to parse unit
            unit = self._parse_row(row, col_mapping, currency)
            if unit:
                unit.raw_row = raw_row
                result.units.append(unit)
        
        return result
    
    def _parse_row(
        self, 
        row: pd.Series, 
        col_mapping: Dict[str, int],
        currency: str
    ) -> Optional[ParsedUnit]:
        """Parse a single row into ParsedUnit."""
        
        # Get unit number (required)
        unit_number = None
        if 'unit_number' in col_mapping:
            col_idx = col_mapping['unit_number']
            if col_idx < len(row):
                unit_number = str(row.iloc[col_idx]).strip()
        
        if not unit_number or unit_number.lower() in ['nan', 'none', '']:
            return None
        
        # Parse other fields
        unit = ParsedUnit(unit_number=unit_number, currency=currency)
        
        # Bedrooms
        if 'bedrooms' in col_mapping:
            value = row.iloc[col_mapping['bedrooms']]
            unit.bedrooms = self.parse_bedrooms(value)
        
        # Area
        if 'area' in col_mapping:
            value = row.iloc[col_mapping['area']]
            unit.area_sqm = self.parse_area(value)
        
        # Floor
        if 'floor' in col_mapping:
            value = row.iloc[col_mapping['floor']]
            unit.floor = self.parse_floor(value)
        
        # Price
        if 'price' in col_mapping:
            value = row.iloc[col_mapping['price']]
            unit.price = self.parse_price(value)
            # Calculate price per sqm
            if unit.price and unit.area_sqm:
                unit.price_per_sqm = round(unit.price / unit.area_sqm, 2)
        
        # Status
        if 'status' in col_mapping:
            value = row.iloc[col_mapping['status']]
            if pd.notna(value):
                unit.status = ParsedUnit._parse_status(str(value))
        
        # View
        if 'view' in col_mapping:
            value = row.iloc[col_mapping['view']]
            if pd.notna(value):
                unit.view_type = str(value).strip()
        
        # Building
        if 'building' in col_mapping:
            value = row.iloc[col_mapping['building']]
            if pd.notna(value):
                unit.building = str(value).strip()
        
        # Layout
        if 'layout' in col_mapping:
            value = row.iloc[col_mapping['layout']]
            if pd.notna(value):
                unit.layout_type = str(value).strip()
                # Try to extract bedrooms from layout if not found
                if unit.bedrooms is None:
                    unit.bedrooms = ParsedUnit._extract_bedrooms_from_layout(unit.layout_type)
        
        # Phase
        if 'phase' in col_mapping:
            value = row.iloc[col_mapping['phase']]
            if pd.notna(value):
                unit.phase = str(value).strip()
        
        # Re-validate after parsing
        unit._validate()
        
        return unit
    
    async def parse_multi_sheet(self, file_path: str, **kwargs) -> Dict[str, ParsingResult]:
        """Parse all sheets in an Excel file."""
        results = {}
        
        try:
            xlsx = pd.ExcelFile(file_path)
            for sheet_name in xlsx.sheet_names:
                result = await self.parse(file_path, sheet_name=sheet_name, **kwargs)
                results[sheet_name] = result
        except Exception as e:
            logger.error(f"Multi-sheet parsing failed: {e}")
            results['error'] = ParsingResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__
            )
        
        return results


class CSVPriceParser(ExcelPriceParser):
    """Alias for CSV parsing using Excel parser."""
    
    SUPPORTED_EXTENSIONS = ['.csv']
