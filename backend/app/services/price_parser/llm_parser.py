"""
LLM-based price parser for complex/non-standard PDFs.
Uses OpenAI GPT-4 Vision or text extraction + GPT-4.
"""
import os
import time
import json
import base64
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile

import pdfplumber
from pdf2image import convert_from_path

from .base import (
    BasePriceParser, ParsedUnit, ParsedPriceData, ParsingResult, UnitStatus
)

logger = logging.getLogger(__name__)


class LLMPriceParser(BasePriceParser):
    """Parser using LLM for complex PDFs."""
    
    # JSON schema for structured output
    OUTPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "developer_name": {"type": "string"},
            "currency": {"type": "string", "enum": ["THB", "USD", "EUR", "IDR", "RUB"]},
            "units": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "unit_number": {"type": "string"},
                        "bedrooms": {"type": "integer"},
                        "bathrooms": {"type": "integer"},
                        "area_sqm": {"type": "number"},
                        "floor": {"type": "integer"},
                        "building": {"type": "string"},
                        "price": {"type": "number"},
                        "price_per_sqm": {"type": "number"},
                        "layout_type": {"type": "string"},
                        "view_type": {"type": "string"},
                        "status": {"type": "string", "enum": ["available", "reserved", "sold", "unknown"]},
                        "phase": {"type": "string"}
                    },
                    "required": ["unit_number"]
                }
            },
            "payment_plans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "schedule": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "milestone": {"type": "string"},
                                    "percentage": {"type": "number"},
                                    "amount": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "required": ["units"]
    }
    
    EXTRACTION_PROMPT = """You are a real estate data extraction expert. Extract unit/apartment information from the provided price list document.

Instructions:
1. Extract ALL units from the document
2. For each unit, extract as much information as possible
3. Currency should be detected from the document (THB for Thailand, USD for US dollars, etc.)
4. If a field is unclear or missing, omit it
5. Status should be one of: available, reserved, sold, unknown
6. Always include unit_number for each unit
7. Convert any abbreviated formats:
   - "1BR" = 1 bedroom
   - "Studio" = 0 bedrooms
   - "2B/2B" = 2 bedrooms, 2 bathrooms
8. Prices may be formatted as "3.5M" = 3,500,000 or "350K" = 350,000

Return ONLY valid JSON matching this schema:
{schema}

DO NOT include any explanatory text, only the JSON object."""

    VISION_PROMPT = """You are a real estate data extraction expert. Analyze this image of a price list/availability sheet and extract all unit information.

Instructions:
1. Carefully read all tables and data in the image
2. Extract every unit listed with its details
3. Pay attention to column headers to understand what each column represents
4. Convert currency symbols to codes (฿ = THB, $ = USD, € = EUR, etc.)
5. Status might be indicated by colors, checkmarks, or text

Return ONLY valid JSON matching this schema:
{schema}

DO NOT include any explanatory text, only the JSON object."""

    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        use_vision: bool = True,
        max_tokens: int = 4096
    ):
        """
        Initialize LLM parser.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o for vision support)
            use_vision: Whether to use vision mode for PDFs
            max_tokens: Max tokens for response
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.use_vision = use_vision
        self.max_tokens = max_tokens
        self._client = None
    
    def can_parse(self, file_path: str) -> bool:
        """LLM parser can handle any PDF."""
        ext = Path(file_path).suffix.lower()
        return ext == '.pdf'
    
    def _get_client(self):
        """Get OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required for LLM parser")
        return self._client
    
    async def parse(self, file_path: str, **kwargs) -> ParsingResult:
        """
        Parse PDF using LLM.
        
        Keyword args:
            use_vision: bool - Override default vision setting
            pages: list - Specific pages to process
            project_context: dict - Additional context about the project
        """
        start_time = time.time()
        result = ParsingResult(parsing_method='llm')
        
        try:
            use_vision = kwargs.get('use_vision', self.use_vision)
            
            if use_vision:
                result = await self._parse_with_vision(file_path, **kwargs)
            else:
                result = await self._parse_with_text(file_path, **kwargs)
            
            result.parsing_time_ms = int((time.time() - start_time) * 1000)
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
            result.parsing_time_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    async def _parse_with_vision(self, file_path: str, **kwargs) -> ParsingResult:
        """Parse PDF by converting to images and using vision model."""
        result = ParsingResult(parsing_method='llm_vision')
        
        try:
            # Convert PDF to images
            pages = kwargs.get('pages')
            images = convert_from_path(
                file_path, 
                dpi=150,  # Balance between quality and size
                first_page=pages[0] if pages else None,
                last_page=pages[-1] if pages else None
            )
            
            if not images:
                result.success = False
                result.error_message = "Could not convert PDF to images"
                return result
            
            # Process images (limit to first 5 pages to avoid token limits)
            max_pages = min(len(images), 5)
            all_units = []
            project_info = {}
            
            client = self._get_client()
            
            for i, image in enumerate(images[:max_pages]):
                logger.info(f"Processing page {i+1}/{max_pages} with vision")
                
                # Convert image to base64
                import io
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Prepare prompt
                prompt = self.VISION_PROMPT.format(schema=json.dumps(self.OUTPUT_SCHEMA, indent=2))
                
                # Call vision API
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_data}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.1
                )
                
                # Parse response
                content = response.choices[0].message.content
                page_data = self._parse_json_response(content)
                
                if page_data:
                    # Merge units
                    if 'units' in page_data:
                        all_units.extend(page_data['units'])
                    
                    # Get project info from first page
                    if i == 0:
                        project_info = {
                            k: v for k, v in page_data.items() 
                            if k not in ['units', 'payment_plans']
                        }
            
            # Convert to ParsedPriceData
            parsed_data = self._convert_to_parsed_data(all_units, project_info)
            
            result.success = True
            result.data = parsed_data
            
            if parsed_data.invalid_count > 0:
                result.warnings.append(
                    f"{parsed_data.invalid_count} units had validation errors"
                )
            
            logger.info(f"LLM vision parsed {parsed_data.valid_count} valid units")
            
        except Exception as e:
            logger.error(f"Vision parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        return result
    
    async def _parse_with_text(self, file_path: str, **kwargs) -> ParsingResult:
        """Parse PDF by extracting text and using text completion."""
        result = ParsingResult(parsing_method='llm_text')
        
        try:
            # Extract text from PDF
            text_content = self._extract_text(file_path)
            
            if not text_content or len(text_content.strip()) < 50:
                result.success = False
                result.error_message = "Could not extract meaningful text from PDF"
                return result
            
            # Truncate if too long (GPT-4 has ~128k context)
            max_chars = 50000
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars]
                result.warnings.append("Text truncated due to length")
            
            client = self._get_client()
            
            # Prepare prompt
            prompt = self.EXTRACTION_PROMPT.format(
                schema=json.dumps(self.OUTPUT_SCHEMA, indent=2)
            )
            
            # Add project context if provided
            project_context = kwargs.get('project_context')
            if project_context:
                prompt += f"\n\nAdditional context about this project:\n{json.dumps(project_context)}"
            
            # Call API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Extract unit data from this price list:\n\n{text_content}"}
                ],
                max_tokens=self.max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            data = self._parse_json_response(content)
            
            if not data or 'units' not in data:
                result.success = False
                result.error_message = "LLM did not return valid unit data"
                return result
            
            # Convert to ParsedPriceData
            project_info = {k: v for k, v in data.items() if k not in ['units', 'payment_plans']}
            parsed_data = self._convert_to_parsed_data(data['units'], project_info)
            
            # Add payment plans if found
            if 'payment_plans' in data:
                parsed_data.payment_plans = data['payment_plans']
            
            result.success = True
            result.data = parsed_data
            
            if parsed_data.invalid_count > 0:
                result.warnings.append(
                    f"{parsed_data.invalid_count} units had validation errors"
                )
            
            logger.info(f"LLM text parsed {parsed_data.valid_count} valid units")
            
        except Exception as e:
            logger.error(f"Text parsing failed: {e}")
            result.success = False
            result.error_message = str(e)
            result.error_type = type(e).__name__
        
        return result
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                
                # Also try to extract tables as text
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        table_text = '\n'.join(['\t'.join(str(c) if c else '' for c in row) for row in table])
                        text_parts.append(table_text)
        
        return '\n\n'.join(text_parts)
    
    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        try:
            # Try direct JSON parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Could not parse JSON from response: {content[:500]}")
        return None
    
    def _convert_to_parsed_data(
        self, 
        units_data: List[Dict], 
        project_info: Dict
    ) -> ParsedPriceData:
        """Convert LLM output to ParsedPriceData."""
        result = ParsedPriceData()
        
        # Set project info
        result.project_name = project_info.get('project_name')
        result.developer_name = project_info.get('developer_name')
        result.currency = project_info.get('currency', 'THB')
        
        # Convert units
        for unit_data in units_data:
            if not unit_data.get('unit_number'):
                continue
            
            # Parse status
            status_str = unit_data.get('status', 'unknown')
            status = ParsedUnit._parse_status(status_str)
            
            unit = ParsedUnit(
                unit_number=str(unit_data['unit_number']),
                bedrooms=unit_data.get('bedrooms'),
                bathrooms=unit_data.get('bathrooms'),
                area_sqm=unit_data.get('area_sqm'),
                floor=unit_data.get('floor'),
                building=unit_data.get('building'),
                price=unit_data.get('price'),
                price_per_sqm=unit_data.get('price_per_sqm'),
                currency=result.currency,
                layout_type=unit_data.get('layout_type'),
                view_type=unit_data.get('view_type'),
                status=status,
                phase=unit_data.get('phase'),
                raw_row=unit_data
            )
            
            result.units.append(unit)
        
        return result
    
    async def parse_with_context(
        self,
        file_path: str,
        project_name: str,
        expected_units: int = None,
        known_buildings: List[str] = None,
        known_layouts: List[str] = None,
        **kwargs
    ) -> ParsingResult:
        """
        Parse with additional project context for better accuracy.
        
        Args:
            file_path: PDF file path
            project_name: Name of the project
            expected_units: Expected number of units (for validation)
            known_buildings: List of building names in project
            known_layouts: List of known layout types
        """
        project_context = {
            'project_name': project_name,
            'expected_units': expected_units,
            'known_buildings': known_buildings,
            'known_layouts': known_layouts
        }
        
        # Filter None values
        project_context = {k: v for k, v in project_context.items() if v is not None}
        
        return await self.parse(file_path, project_context=project_context, **kwargs)
