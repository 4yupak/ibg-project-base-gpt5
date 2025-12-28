"""
Price-related Celery tasks.
"""
import os
import tempfile
import asyncio
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from celery import shared_task

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _process_price_file_async(
    price_version_id: int,
    file_path: str,
    source_type: str,
    project_id: int,
    user_id: Optional[int] = None
):
    """Async implementation of price file processing."""
    from app.db.database import async_session_maker
    from app.services.price_parser import PriceParserFactory
    from app.services.price_ingestion_service import ingest_price_data
    from app.models.price import PriceVersion, PriceVersionStatus
    
    async with async_session_maker() as db:
        try:
            # Get price version
            version = await db.get(PriceVersion, price_version_id)
            if not version:
                logger.error(f"PriceVersion {price_version_id} not found")
                return {
                    'status': 'failed',
                    'error': 'Price version not found'
                }
            
            # Update status
            version.status = PriceVersionStatus.PROCESSING
            version.processing_started_at = datetime.utcnow()
            await db.commit()
            
            # Create parser factory
            factory = PriceParserFactory(
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                google_credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH')
            )
            
            # Parse file
            logger.info(f"Parsing file {file_path} for version {price_version_id}")
            result = await factory.parse(file_path, use_llm_fallback=True)
            
            if not result.success:
                version.status = PriceVersionStatus.FAILED
                version.errors = [{'message': result.error_message}]
                version.processing_completed_at = datetime.utcnow()
                await db.commit()
                
                return {
                    'status': 'failed',
                    'error': result.error_message,
                    'price_version_id': price_version_id
                }
            
            # Ingest parsed data into database
            logger.info(f"Ingesting {result.data.valid_count} units for version {price_version_id}")
            ingestion_result = await ingest_price_data(
                db=db,
                project_id=project_id,
                price_version_id=price_version_id,
                parsed_data=result.data,
                user_id=user_id
            )
            
            return {
                'status': ingestion_result['status'],
                'price_version_id': price_version_id,
                'statistics': ingestion_result.get('statistics', {}),
                'parsing_method': result.parsing_method,
                'fallback_used': result.fallback_used,
                'warnings': result.warnings
            }
            
        except Exception as e:
            logger.exception(f"Price file processing failed: {e}")
            
            # Update version status
            try:
                version = await db.get(PriceVersion, price_version_id)
                if version:
                    version.status = PriceVersionStatus.FAILED
                    version.errors = [{'message': str(e)}]
                    version.processing_completed_at = datetime.utcnow()
                    await db.commit()
            except Exception:
                pass
            
            return {
                'status': 'failed',
                'error': str(e),
                'price_version_id': price_version_id
            }


@shared_task(name="app.tasks.price_tasks.process_price_file")
def process_price_file(
    price_version_id: int,
    file_path: str,
    source_type: str,
    project_id: int,
    user_id: Optional[int] = None
):
    """
    Process uploaded price file (PDF/Excel).
    
    Steps:
    1. Parse file using appropriate parser
    2. Validate parsed data
    3. Calculate price changes vs existing data
    4. Update database
    5. Create price history records
    
    Args:
        price_version_id: PriceVersion record ID
        file_path: Path to uploaded file
        source_type: Source type (pdf, excel, csv)
        project_id: Project to update
        user_id: User who initiated the upload
    """
    logger.info(f"Processing price file for version {price_version_id}, project {project_id}")
    
    return run_async(_process_price_file_async(
        price_version_id=price_version_id,
        file_path=file_path,
        source_type=source_type,
        project_id=project_id,
        user_id=user_id
    ))


async def _process_google_sheet_async(
    price_version_id: int,
    sheet_url: str,
    project_id: int,
    sheet_name: Optional[str] = None,
    user_id: Optional[int] = None
):
    """Async implementation of Google Sheets processing."""
    from app.db.database import async_session_maker
    from app.services.price_parser import PriceParserFactory
    from app.services.price_ingestion_service import ingest_price_data
    from app.models.price import PriceVersion, PriceVersionStatus
    
    async with async_session_maker() as db:
        try:
            # Get price version
            version = await db.get(PriceVersion, price_version_id)
            if not version:
                return {
                    'status': 'failed',
                    'error': 'Price version not found'
                }
            
            # Update status
            version.status = PriceVersionStatus.PROCESSING
            version.processing_started_at = datetime.utcnow()
            await db.commit()
            
            # Create parser factory
            factory = PriceParserFactory(
                google_credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH'),
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            
            # Parse Google Sheet
            logger.info(f"Parsing Google Sheet {sheet_url}")
            result = await factory.parse(
                sheet_url,
                sheet_name=sheet_name,
                use_llm_fallback=True
            )
            
            if not result.success:
                version.status = PriceVersionStatus.FAILED
                version.errors = [{'message': result.error_message}]
                version.processing_completed_at = datetime.utcnow()
                await db.commit()
                
                return {
                    'status': 'failed',
                    'error': result.error_message
                }
            
            # Ingest data
            ingestion_result = await ingest_price_data(
                db=db,
                project_id=project_id,
                price_version_id=price_version_id,
                parsed_data=result.data,
                user_id=user_id
            )
            
            return {
                'status': ingestion_result['status'],
                'price_version_id': price_version_id,
                'statistics': ingestion_result.get('statistics', {}),
                'warnings': result.warnings
            }
            
        except Exception as e:
            logger.exception(f"Google Sheet processing failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }


@shared_task(name="app.tasks.price_tasks.process_google_sheet")
def process_google_sheet(
    price_version_id: int,
    sheet_url: str,
    project_id: int,
    sheet_name: Optional[str] = None,
    user_id: Optional[int] = None
):
    """
    Process Google Sheets price data.
    
    Args:
        price_version_id: PriceVersion record ID
        sheet_url: Google Sheets URL
        project_id: Project ID
        sheet_name: Specific sheet name to parse (optional)
        user_id: User who initiated the upload
    """
    logger.info(f"Processing Google Sheet for version {price_version_id}")
    
    return run_async(_process_google_sheet_async(
        price_version_id=price_version_id,
        sheet_url=sheet_url,
        project_id=project_id,
        sheet_name=sheet_name,
        user_id=user_id
    ))


async def _check_gsheets_updates_async():
    """Check all linked Google Sheets for updates."""
    from app.db.database import async_session_maker
    from sqlalchemy import select
    from app.models.price import PriceVersion, PriceVersionStatus, PriceSourceType
    from app.services.price_parser import GoogleSheetsParser
    
    checked = 0
    updated = 0
    
    async with async_session_maker() as db:
        # Get all approved Google Sheets sources
        result = await db.execute(
            select(PriceVersion)
            .where(
                PriceVersion.source_type == PriceSourceType.GOOGLE_SHEETS,
                PriceVersion.status == PriceVersionStatus.APPROVED,
                PriceVersion.source_url.isnot(None)
            )
            .distinct(PriceVersion.project_id, PriceVersion.source_url)
        )
        versions = result.scalars().all()
        
        parser = GoogleSheetsParser(
            credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH')
        )
        
        for version in versions:
            checked += 1
            
            try:
                # Get last modified time
                last_modified = await parser.get_last_modified(version.source_url)
                
                if last_modified:
                    # Compare with our last update
                    if version.processing_completed_at:
                        sheet_modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                        if sheet_modified > version.processing_completed_at:
                            # Sheet has been updated - trigger new processing
                            logger.info(f"Google Sheet updated for project {version.project_id}")
                            
                            # Create new price version
                            from app.models.price import PriceVersion
                            from sqlalchemy import func
                            
                            max_version = await db.execute(
                                select(func.max(PriceVersion.version_number))
                                .where(PriceVersion.project_id == version.project_id)
                            )
                            next_version = (max_version.scalar() or 0) + 1
                            
                            new_version = PriceVersion(
                                project_id=version.project_id,
                                version_number=next_version,
                                source_type=PriceSourceType.GOOGLE_SHEETS,
                                source_url=version.source_url,
                                status=PriceVersionStatus.PENDING,
                                original_currency=version.original_currency
                            )
                            db.add(new_version)
                            await db.commit()
                            await db.refresh(new_version)
                            
                            # Queue processing task
                            process_google_sheet.delay(
                                price_version_id=new_version.id,
                                sheet_url=version.source_url,
                                project_id=version.project_id
                            )
                            
                            updated += 1
                            
            except Exception as e:
                logger.warning(f"Failed to check sheet {version.source_url}: {e}")
    
    return {'checked': checked, 'updated': updated}


@shared_task(name="app.tasks.price_tasks.check_gsheets_updates")
def check_gsheets_updates():
    """
    Check all linked Google Sheets for updates.
    Triggered periodically by Celery Beat.
    """
    logger.info("Checking Google Sheets for updates")
    return run_async(_check_gsheets_updates_async())


async def _parse_with_llm_async(
    price_version_id: int,
    file_path: str,
    project_id: int,
    project_name: Optional[str] = None,
    user_id: Optional[int] = None
):
    """Use LLM to parse complex PDF."""
    from app.db.database import async_session_maker
    from app.services.price_parser import LLMPriceParser
    from app.services.price_ingestion_service import ingest_price_data
    from app.models.price import PriceVersion, PriceVersionStatus
    
    async with async_session_maker() as db:
        try:
            version = await db.get(PriceVersion, price_version_id)
            if not version:
                return {'status': 'failed', 'error': 'Version not found'}
            
            # Update status
            version.status = PriceVersionStatus.PROCESSING
            version.processing_started_at = datetime.utcnow()
            await db.commit()
            
            # Use LLM parser
            parser = LLMPriceParser(
                api_key=os.getenv('OPENAI_API_KEY'),
                model='gpt-4o',
                use_vision=True
            )
            
            # Parse with context if project name provided
            if project_name:
                result = await parser.parse_with_context(
                    file_path=file_path,
                    project_name=project_name
                )
            else:
                result = await parser.parse(file_path)
            
            if not result.success:
                version.status = PriceVersionStatus.FAILED
                version.errors = [{'message': result.error_message}]
                version.processing_completed_at = datetime.utcnow()
                await db.commit()
                
                return {
                    'status': 'failed',
                    'error': result.error_message,
                    'method': 'llm'
                }
            
            # Ingest data
            ingestion_result = await ingest_price_data(
                db=db,
                project_id=project_id,
                price_version_id=price_version_id,
                parsed_data=result.data,
                user_id=user_id
            )
            
            return {
                'status': ingestion_result['status'],
                'method': 'llm',
                'price_version_id': price_version_id,
                'statistics': ingestion_result.get('statistics', {}),
                'warnings': result.warnings
            }
            
        except Exception as e:
            logger.exception(f"LLM parsing failed: {e}")
            return {'status': 'failed', 'error': str(e), 'method': 'llm'}


@shared_task(name="app.tasks.price_tasks.parse_pdf_with_llm")
def parse_pdf_with_llm(
    price_version_id: int,
    file_path: str,
    project_id: int,
    project_name: Optional[str] = None,
    user_id: Optional[int] = None
):
    """
    Parse non-standard PDF using LLM extraction.
    Fallback when tabular extraction fails.
    
    Args:
        price_version_id: PriceVersion record ID
        file_path: Path to PDF file
        project_id: Project ID
        project_name: Project name for context
        user_id: User ID
    """
    logger.info(f"LLM parsing for price version {price_version_id}")
    
    return run_async(_parse_with_llm_async(
        price_version_id=price_version_id,
        file_path=file_path,
        project_id=project_id,
        project_name=project_name,
        user_id=user_id
    ))


async def _calculate_price_changes_async(project_id: int, price_version_id: int):
    """Calculate and record all price changes for a version."""
    from app.db.database import async_session_maker
    from sqlalchemy import select
    from app.models.price import PriceHistory
    from app.models.unit import Unit
    
    async with async_session_maker() as db:
        # Get all price history for this version
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.price_version_id == price_version_id)
        )
        history_records = result.scalars().all()
        
        changes_recorded = len(history_records)
        
        # Summary statistics
        increases = sum(1 for h in history_records if h.change_type == 'increase')
        decreases = sum(1 for h in history_records if h.change_type == 'decrease')
        status_changes = sum(1 for h in history_records if h.change_type == 'status_change')
        
        return {
            'project_id': project_id,
            'price_version_id': price_version_id,
            'changes_recorded': changes_recorded,
            'increases': increases,
            'decreases': decreases,
            'status_changes': status_changes
        }


@shared_task(name="app.tasks.price_tasks.calculate_price_changes")
def calculate_price_changes(project_id: int, price_version_id: int):
    """
    Calculate price changes and update PriceHistory.
    Typically called after ingestion to generate summary statistics.
    
    Args:
        project_id: Project ID
        price_version_id: PriceVersion ID
    """
    logger.info(f"Calculating price changes for project {project_id}")
    return run_async(_calculate_price_changes_async(project_id, price_version_id))


async def _process_file_content_async(
    price_version_id: int,
    file_content: bytes,
    filename: str,
    project_id: int,
    user_id: Optional[int] = None
):
    """Process file from content bytes."""
    from app.db.database import async_session_maker
    from app.services.price_parser import PriceParserFactory
    from app.services.price_ingestion_service import ingest_price_data
    from app.models.price import PriceVersion, PriceVersionStatus
    
    # Save to temp file
    ext = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    
    try:
        async with async_session_maker() as db:
            version = await db.get(PriceVersion, price_version_id)
            if not version:
                return {'status': 'failed', 'error': 'Version not found'}
            
            version.status = PriceVersionStatus.PROCESSING
            version.processing_started_at = datetime.utcnow()
            await db.commit()
            
            # Parse file
            factory = PriceParserFactory(
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            result = await factory.parse(tmp_path, use_llm_fallback=True)
            
            if not result.success:
                version.status = PriceVersionStatus.FAILED
                version.errors = [{'message': result.error_message}]
                version.processing_completed_at = datetime.utcnow()
                await db.commit()
                return {'status': 'failed', 'error': result.error_message}
            
            # Ingest
            ingestion_result = await ingest_price_data(
                db=db,
                project_id=project_id,
                price_version_id=price_version_id,
                parsed_data=result.data,
                user_id=user_id
            )
            
            return {
                'status': ingestion_result['status'],
                'statistics': ingestion_result.get('statistics', {}),
                'warnings': result.warnings
            }
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@shared_task(name="app.tasks.price_tasks.process_file_content")
def process_file_content(
    price_version_id: int,
    file_content: bytes,
    filename: str,
    project_id: int,
    user_id: Optional[int] = None
):
    """
    Process file from raw bytes content.
    
    Useful when file content is passed directly instead of path.
    """
    logger.info(f"Processing file content {filename} for version {price_version_id}")
    
    return run_async(_process_file_content_async(
        price_version_id=price_version_id,
        file_content=file_content,
        filename=filename,
        project_id=project_id,
        user_id=user_id
    ))
