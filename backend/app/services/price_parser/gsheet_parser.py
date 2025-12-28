"""
Google Sheets price parser.
Authenticates via service account and parses sheet data.
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional
import re

import pandas as pd

from .base import (
    BasePriceParser, ParsedUnit, ParsedPriceData, ParsingResult, UnitStatus
)
from .excel_parser import ExcelPriceParser

logger = logging.getLogger(__name__)


class GoogleSheetsParser(BasePriceParser):
    """Parser for Google Sheets."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize with optional service account credentials.
        
        Args:
            credentials_path: Path to service account JSON file
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self._client = None
    
    def can_parse(self, file_path: str) -> bool:
        """Check if URL is a Google Sheets link."""
        return self._is_google_sheets_url(file_path)
    
    def _is_google_sheets_url(self, url: str) -> bool:
        """Check if URL is a Google Sheets URL."""
        patterns = [
            r'docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'sheets\.google\.com',
        ]
        return any(re.search(p, url) for p in patterns)
    
    def _extract_sheet_id(self, url: str) -> Optional[str]:
        """Extract sheet ID from Google Sheets URL."""
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return None
    
    def _get_client(self):
        """Get authenticated gspread client."""
        if self._client is None:
            try:
                import gspread
                from google.oauth2.service_account import Credentials
                
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets.readonly',
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
                
                if self.credentials_path and os.path.exists(self.credentials_path):
                    creds = Credentials.from_service_account_file(
                        self.credentials_path, 
                        scopes=scopes
                    )
                else:
                    # Try default credentials
                    from google.auth import default
                    creds, _ = default(scopes=scopes)
                
                self._client = gspread.authorize(creds)
                
            except ImportError:
                logger.error("gspread not installed")
                raise ImportError("gspread and google-auth packages required")
            except Exception as e:
                logger.error(f"Failed to authenticate with Google: {e}")
                raise
        
        return self._client
    
    async def parse(self, file_path: str, **kwargs) -> ParsingResult:
        """
        Parse Google Sheets.
        
        Args:
            file_path: Google Sheets URL
            sheet_name: Name of worksheet (default: first sheet)
            range: A1 notation range to read (default: all)
            currency: Force currency
        """
        start_time = time.time()
        result = ParsingResult(parsing_method='google_sheets')
        
        try:
            # Extract sheet ID
            sheet_id = self._extract_sheet_id(file_path)
            if not sheet_id:
                raise ValueError(f"Invalid Google Sheets URL: {file_path}")
            
            # Get client
            client = self._get_client()
            
            # Open spreadsheet
            spreadsheet = client.open_by_key(sheet_id)
            
            # Get worksheet
            sheet_name = kwargs.get('sheet_name')
            if sheet_name:
                worksheet = spreadsheet.worksheet(sheet_name)
            else:
                worksheet = spreadsheet.sheet1
            
            # Get all values
            cell_range = kwargs.get('range')
            if cell_range:
                values = worksheet.get(cell_range)
            else:
                values = worksheet.get_all_values()
            
            if not values:
                result.success = False
                result.error_message = "No data found in sheet"
                result.error_type = "EmptySheet"
                return result
            
            # Convert to DataFrame for processing
            df = pd.DataFrame(values[1:], columns=values[0])
            
            # Use Excel parser logic for consistent processing
            excel_parser = ExcelPriceParser()
            parsed_data = excel_parser._parse_dataframe(df, **kwargs)
            
            result.success = True
            result.data = parsed_data
            result.parsing_time_ms = int((time.time() - start_time) * 1000)
            
            if parsed_data.invalid_count > 0:
                result.warnings.append(
                    f"{parsed_data.invalid_count} units had validation errors"
                )
            
            logger.info(f"Google Sheets parsed {parsed_data.valid_count} valid units")
            
        except ImportError as e:
            result.success = False
            result.error_message = str(e)
            result.error_type = "DependencyMissing"
        except Exception as e:
            logger.error(f"Google Sheets parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.parsing_time_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    async def list_sheets(self, url: str) -> List[str]:
        """List all worksheets in a Google Sheets document."""
        try:
            sheet_id = self._extract_sheet_id(url)
            if not sheet_id:
                return []
            
            client = self._get_client()
            spreadsheet = client.open_by_key(sheet_id)
            
            return [ws.title for ws in spreadsheet.worksheets()]
            
        except Exception as e:
            logger.error(f"Failed to list sheets: {e}")
            return []
    
    async def get_last_modified(self, url: str) -> Optional[str]:
        """Get last modified time of Google Sheets (for change detection)."""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials
            
            sheet_id = self._extract_sheet_id(url)
            if not sheet_id:
                return None
            
            scopes = ['https://www.googleapis.com/auth/drive.metadata.readonly']
            creds = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=scopes
            )
            
            drive_service = build('drive', 'v3', credentials=creds)
            file = drive_service.files().get(
                fileId=sheet_id, 
                fields='modifiedTime'
            ).execute()
            
            return file.get('modifiedTime')
            
        except Exception as e:
            logger.error(f"Failed to get last modified: {e}")
            return None
