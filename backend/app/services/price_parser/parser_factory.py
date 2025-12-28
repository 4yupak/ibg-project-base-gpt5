"""
Price parser factory.
Selects appropriate parser based on file type and content.
"""
import os
import logging
from typing import Optional, List
from pathlib import Path
from enum import Enum

from .base import BasePriceParser, ParsingResult
from .excel_parser import ExcelPriceParser
from .pdf_parser import PDFPriceParser
from .gsheet_parser import GoogleSheetsParser
from .llm_parser import LLMPriceParser

logger = logging.getLogger(__name__)


class ParserType(str, Enum):
    """Available parser types."""
    EXCEL = "excel"
    PDF = "pdf"
    GOOGLE_SHEETS = "google_sheets"
    LLM = "llm"
    AUTO = "auto"


class PriceParserFactory:
    """
    Factory for creating and managing price parsers.
    
    Supports:
    - Automatic parser selection based on file type
    - Fallback to LLM parser for failed extractions
    - Parser configuration and caching
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        google_credentials_path: Optional[str] = None,
        llm_model: str = "gpt-4o",
        enable_llm_fallback: bool = True
    ):
        """
        Initialize factory.
        
        Args:
            openai_api_key: API key for OpenAI (for LLM parser)
            google_credentials_path: Path to Google service account JSON
            llm_model: Model to use for LLM parser
            enable_llm_fallback: Whether to use LLM as fallback
        """
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.google_credentials_path = google_credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.llm_model = llm_model
        self.enable_llm_fallback = enable_llm_fallback
        
        # Parser instances (lazy loaded)
        self._parsers = {}
    
    def get_parser(self, parser_type: ParserType) -> BasePriceParser:
        """Get parser instance by type."""
        if parser_type not in self._parsers:
            self._parsers[parser_type] = self._create_parser(parser_type)
        return self._parsers[parser_type]
    
    def _create_parser(self, parser_type: ParserType) -> BasePriceParser:
        """Create parser instance."""
        if parser_type == ParserType.EXCEL:
            return ExcelPriceParser()
        elif parser_type == ParserType.PDF:
            return PDFPriceParser()
        elif parser_type == ParserType.GOOGLE_SHEETS:
            return GoogleSheetsParser(credentials_path=self.google_credentials_path)
        elif parser_type == ParserType.LLM:
            return LLMPriceParser(
                api_key=self.openai_api_key,
                model=self.llm_model
            )
        else:
            raise ValueError(f"Unknown parser type: {parser_type}")
    
    def detect_parser_type(self, file_path_or_url: str) -> ParserType:
        """
        Detect appropriate parser type based on file path or URL.
        
        Args:
            file_path_or_url: File path or URL
            
        Returns:
            ParserType enum value
        """
        # Check if it's a URL
        if file_path_or_url.startswith(('http://', 'https://')):
            # Google Sheets
            if 'docs.google.com/spreadsheets' in file_path_or_url or 'sheets.google.com' in file_path_or_url:
                return ParserType.GOOGLE_SHEETS
            
            # Other URLs - try to determine from extension
            url_path = file_path_or_url.split('?')[0]
            ext = Path(url_path).suffix.lower()
        else:
            ext = Path(file_path_or_url).suffix.lower()
        
        # Map extension to parser type
        extension_map = {
            '.xlsx': ParserType.EXCEL,
            '.xls': ParserType.EXCEL,
            '.csv': ParserType.EXCEL,
            '.pdf': ParserType.PDF,
        }
        
        return extension_map.get(ext, ParserType.LLM)
    
    async def parse(
        self,
        file_path_or_url: str,
        parser_type: ParserType = ParserType.AUTO,
        use_llm_fallback: Optional[bool] = None,
        **kwargs
    ) -> ParsingResult:
        """
        Parse a price file using appropriate parser.
        
        Args:
            file_path_or_url: Path to file or URL
            parser_type: Explicit parser type (default: auto-detect)
            use_llm_fallback: Override default LLM fallback setting
            **kwargs: Additional arguments passed to parser
            
        Returns:
            ParsingResult with parsed data or error info
        """
        # Determine parser type
        if parser_type == ParserType.AUTO:
            parser_type = self.detect_parser_type(file_path_or_url)
        
        logger.info(f"Parsing {file_path_or_url} with {parser_type.value} parser")
        
        # Get parser
        parser = self.get_parser(parser_type)
        
        # Parse
        result = await parser.parse(file_path_or_url, **kwargs)
        
        # Check if we should try LLM fallback
        use_fallback = use_llm_fallback if use_llm_fallback is not None else self.enable_llm_fallback
        
        if not result.success or (result.data and result.data.valid_count == 0):
            if use_fallback and parser_type != ParserType.LLM:
                logger.info(f"Primary parser failed, trying LLM fallback")
                
                llm_parser = self.get_parser(ParserType.LLM)
                result = await llm_parser.parse(file_path_or_url, **kwargs)
                result.fallback_used = True
        
        return result
    
    async def parse_file_content(
        self,
        file_content: bytes,
        filename: str,
        parser_type: ParserType = ParserType.AUTO,
        **kwargs
    ) -> ParsingResult:
        """
        Parse from file content (bytes).
        
        Saves content to temp file and parses.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename (for extension detection)
            parser_type: Parser type to use
            **kwargs: Additional parser arguments
        """
        import tempfile
        
        # Determine extension
        ext = Path(filename).suffix.lower()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            return await self.parse(tmp_path, parser_type=parser_type, **kwargs)
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    async def validate_file(self, file_path_or_url: str) -> dict:
        """
        Validate file without full parsing.
        
        Returns quick validation info:
        - File type detected
        - Parser to be used
        - Basic file info (size, pages for PDF, etc.)
        - Whether LLM fallback is available
        """
        result = {
            'valid': True,
            'file_type': None,
            'parser_type': None,
            'file_info': {},
            'warnings': [],
            'llm_fallback_available': bool(self.openai_api_key)
        }
        
        try:
            # Detect parser type
            parser_type = self.detect_parser_type(file_path_or_url)
            result['parser_type'] = parser_type.value
            
            # Get file info based on type
            if parser_type == ParserType.PDF:
                result['file_type'] = 'pdf'
                import pdfplumber
                with pdfplumber.open(file_path_or_url) as pdf:
                    result['file_info'] = {
                        'pages': len(pdf.pages),
                        'metadata': pdf.metadata or {}
                    }
            
            elif parser_type == ParserType.EXCEL:
                ext = Path(file_path_or_url).suffix.lower()
                result['file_type'] = 'excel' if ext in ['.xlsx', '.xls'] else 'csv'
                
                import pandas as pd
                if ext == '.csv':
                    df = pd.read_csv(file_path_or_url, nrows=5)
                else:
                    xl = pd.ExcelFile(file_path_or_url)
                    result['file_info']['sheets'] = xl.sheet_names
                    df = pd.read_excel(file_path_or_url, nrows=5)
                
                result['file_info']['columns'] = list(df.columns)
                result['file_info']['estimated_rows'] = len(df)
            
            elif parser_type == ParserType.GOOGLE_SHEETS:
                result['file_type'] = 'google_sheets'
                # Can't validate without credentials
                if not self.google_credentials_path:
                    result['warnings'].append('Google credentials not configured')
        
        except Exception as e:
            result['valid'] = False
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def supported_extensions() -> List[str]:
        """Get list of supported file extensions."""
        return ['.xlsx', '.xls', '.csv', '.pdf']
    
    @staticmethod
    def supported_mime_types() -> List[str]:
        """Get list of supported MIME types."""
        return [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'text/csv',
            'application/csv'
        ]


# Singleton instance for convenience
_factory_instance: Optional[PriceParserFactory] = None


def get_parser_factory() -> PriceParserFactory:
    """Get or create singleton factory instance."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = PriceParserFactory()
    return _factory_instance


async def parse_price_file(
    file_path_or_url: str,
    **kwargs
) -> ParsingResult:
    """
    Convenience function to parse a price file.
    
    Uses singleton factory instance.
    """
    factory = get_parser_factory()
    return await factory.parse(file_path_or_url, **kwargs)
