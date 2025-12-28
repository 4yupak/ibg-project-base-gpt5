"""
Price Ingestion Service.
Handles saving parsed data to database, calculating price changes, and managing versions.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.price import PriceVersion, PriceHistory, PriceVersionStatus, ExchangeRate
from app.models.unit import Unit, UnitStatus, UnitType, ViewType
from app.models.project import Project
from app.services.price_parser.base import ParsedPriceData, ParsedUnit, UnitStatus as ParsedUnitStatus

logger = logging.getLogger(__name__)


class PriceIngestionService:
    """
    Service for ingesting parsed price data into database.
    
    Responsibilities:
    - Create/update units from parsed data
    - Calculate and record price changes
    - Handle currency conversion
    - Update price version status
    - Track statistics
    """
    
    # Exchange rates to USD (fallback defaults)
    DEFAULT_EXCHANGE_RATES = {
        'THB': 0.028,  # 1 THB ≈ 0.028 USD
        'USD': 1.0,
        'EUR': 1.08,
        'RUB': 0.011,
        'IDR': 0.000063,
    }
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self._exchange_rates: Dict[str, float] = {}
        self._stats = {
            'created': 0,
            'updated': 0,
            'unchanged': 0,
            'errors': 0,
        }
    
    async def ingest(
        self,
        project_id: int,
        price_version_id: int,
        parsed_data: ParsedPriceData,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main ingestion method.
        
        Args:
            project_id: Project to update units for
            price_version_id: PriceVersion record ID
            parsed_data: Parsed data from parser
            user_id: User performing the ingestion
            
        Returns:
            Ingestion result with statistics
        """
        logger.info(f"Starting ingestion for project {project_id}, version {price_version_id}")
        
        # Reset stats
        self._stats = {'created': 0, 'updated': 0, 'unchanged': 0, 'errors': 0}
        errors: List[Dict[str, Any]] = []
        warnings: List[str] = []
        
        try:
            # Get price version
            version = await self.db.get(PriceVersion, price_version_id)
            if not version:
                raise ValueError(f"PriceVersion {price_version_id} not found")
            
            # Update status to processing
            version.status = PriceVersionStatus.PROCESSING
            version.processing_started_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            # Get project
            project = await self.db.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Load exchange rate
            await self._load_exchange_rate(parsed_data.currency)
            
            # Get existing units for comparison
            existing_units = await self._get_existing_units(project_id)
            existing_by_number = {u.unit_number.upper(): u for u in existing_units}
            
            # Process each parsed unit
            for parsed_unit in parsed_data.valid_units:
                try:
                    result = await self._process_unit(
                        project_id=project_id,
                        price_version_id=price_version_id,
                        parsed_unit=parsed_unit,
                        existing_units=existing_by_number,
                        currency=parsed_data.currency
                    )
                except Exception as e:
                    logger.error(f"Error processing unit {parsed_unit.unit_number}: {e}")
                    errors.append({
                        'unit_number': parsed_unit.unit_number,
                        'error': str(e)
                    })
                    self._stats['errors'] += 1
            
            # Add warnings for invalid units
            for invalid_unit in parsed_data.invalid_units:
                warnings.append(
                    f"Unit {invalid_unit.unit_number}: {', '.join(invalid_unit.validation_errors)}"
                )
            
            # Update price version with results
            version.status = PriceVersionStatus.COMPLETED if not errors else PriceVersionStatus.REQUIRES_REVIEW
            version.processing_completed_at = datetime.now(timezone.utc)
            version.units_created = self._stats['created']
            version.units_updated = self._stats['updated']
            version.units_unchanged = self._stats['unchanged']
            version.units_errors = self._stats['errors']
            version.errors = errors if errors else None
            version.warnings = [{'message': w} for w in warnings] if warnings else None
            
            # Store exchange rate used
            version.exchange_rate_usd = self._exchange_rates.get(parsed_data.currency)
            version.exchange_rate_date = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            # Mark project for review if there were price changes
            if self._stats['updated'] > 0:
                project.requires_review = True
                await self.db.commit()
            
            logger.info(
                f"Ingestion complete: {self._stats['created']} created, "
                f"{self._stats['updated']} updated, {self._stats['unchanged']} unchanged, "
                f"{self._stats['errors']} errors"
            )
            
            return {
                'success': True,
                'statistics': self._stats.copy(),
                'errors': errors,
                'warnings': warnings,
                'price_version_id': price_version_id,
                'status': version.status.value
            }
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            
            # Update version status
            if version:
                version.status = PriceVersionStatus.FAILED
                version.processing_completed_at = datetime.now(timezone.utc)
                version.errors = [{'message': str(e)}]
                await self.db.commit()
            
            return {
                'success': False,
                'error': str(e),
                'statistics': self._stats.copy(),
                'price_version_id': price_version_id,
                'status': 'failed'
            }
    
    async def _get_existing_units(self, project_id: int) -> List[Unit]:
        """Get all existing units for a project."""
        result = await self.db.execute(
            select(Unit).where(
                Unit.project_id == project_id,
                Unit.is_deleted == False
            )
        )
        return list(result.scalars().all())
    
    async def _process_unit(
        self,
        project_id: int,
        price_version_id: int,
        parsed_unit: ParsedUnit,
        existing_units: Dict[str, Unit],
        currency: str
    ) -> str:
        """
        Process a single parsed unit.
        
        Returns: 'created', 'updated', or 'unchanged'
        """
        unit_number = parsed_unit.unit_number.upper()
        existing = existing_units.get(unit_number)
        
        # Convert price to USD
        price_usd = self._convert_to_usd(parsed_unit.price, currency)
        price_per_sqm_usd = self._convert_to_usd(parsed_unit.price_per_sqm, currency)
        
        if existing:
            # Check if anything changed
            price_changed = self._price_changed(existing, parsed_unit, currency)
            details_changed = self._details_changed(existing, parsed_unit)
            status_changed = self._status_changed(existing, parsed_unit)
            
            if not price_changed and not details_changed and not status_changed:
                self._stats['unchanged'] += 1
                return 'unchanged'
            
            # Record price history if price changed
            if price_changed and existing.price is not None:
                await self._create_price_history(
                    unit=existing,
                    new_price=parsed_unit.price,
                    new_price_usd=price_usd,
                    new_status=parsed_unit.status.value if parsed_unit.status else None,
                    price_version_id=price_version_id,
                    currency=currency
                )
            
            # Update unit
            await self._update_unit(
                existing, parsed_unit, price_usd, price_per_sqm_usd, 
                currency, price_version_id
            )
            
            self._stats['updated'] += 1
            return 'updated'
        else:
            # Create new unit
            await self._create_unit(
                project_id, parsed_unit, price_usd, price_per_sqm_usd,
                currency, price_version_id
            )
            
            self._stats['created'] += 1
            return 'created'
    
    async def _create_unit(
        self,
        project_id: int,
        parsed: ParsedUnit,
        price_usd: Optional[float],
        price_per_sqm_usd: Optional[float],
        currency: str,
        price_version_id: int
    ) -> Unit:
        """Create a new unit from parsed data."""
        
        # Determine unit type
        unit_type = self._determine_unit_type(parsed.bedrooms)
        
        # Map view type
        view_type = self._map_view_type(parsed.view_type)
        
        # Map status
        status = self._map_unit_status(parsed.status)
        
        unit = Unit(
            project_id=project_id,
            unit_number=parsed.unit_number.upper(),
            building=parsed.building,
            floor=parsed.floor,
            unit_type=unit_type,
            bedrooms=parsed.bedrooms or 0,
            bathrooms=parsed.bathrooms,
            area_sqm=parsed.area_sqm or 0,
            area_sqft=parsed.area_sqm * 10.764 if parsed.area_sqm else None,
            view_type=view_type,
            price=parsed.price,
            currency=currency,
            price_per_sqm=parsed.price_per_sqm,
            price_usd=price_usd,
            price_per_sqm_usd=price_per_sqm_usd,
            exchange_rate=self._exchange_rates.get(currency),
            exchange_rate_date=datetime.now(timezone.utc),
            status=status,
            status_updated_at=datetime.now(timezone.utc),
            layout_name=parsed.layout_type,
            last_price_update=datetime.now(timezone.utc),
            price_version_id=price_version_id,
            is_active=True
        )
        
        self.db.add(unit)
        await self.db.flush()
        
        return unit
    
    async def _update_unit(
        self,
        unit: Unit,
        parsed: ParsedUnit,
        price_usd: Optional[float],
        price_per_sqm_usd: Optional[float],
        currency: str,
        price_version_id: int
    ):
        """Update existing unit with parsed data."""
        
        # Store previous price for history
        if parsed.price and unit.price and parsed.price != unit.price:
            unit.previous_price = unit.price
            unit.previous_price_usd = unit.price_usd
            unit.price_change_percent = self._calculate_change_percent(unit.price, parsed.price)
            unit.price_changed_at = datetime.now(timezone.utc)
        
        # Update fields
        if parsed.price is not None:
            unit.price = parsed.price
            unit.price_usd = price_usd
            unit.currency = currency
        
        if parsed.price_per_sqm is not None:
            unit.price_per_sqm = parsed.price_per_sqm
            unit.price_per_sqm_usd = price_per_sqm_usd
        
        if parsed.area_sqm is not None:
            unit.area_sqm = parsed.area_sqm
            unit.area_sqft = parsed.area_sqm * 10.764
        
        if parsed.floor is not None:
            unit.floor = parsed.floor
        
        if parsed.building:
            unit.building = parsed.building
        
        if parsed.bedrooms is not None:
            unit.bedrooms = parsed.bedrooms
            unit.unit_type = self._determine_unit_type(parsed.bedrooms)
        
        if parsed.bathrooms is not None:
            unit.bathrooms = parsed.bathrooms
        
        if parsed.view_type:
            unit.view_type = self._map_view_type(parsed.view_type)
        
        if parsed.layout_type:
            unit.layout_name = parsed.layout_type
        
        if parsed.status and parsed.status != ParsedUnitStatus.UNKNOWN:
            unit.status = self._map_unit_status(parsed.status)
            unit.status_updated_at = datetime.now(timezone.utc)
        
        # Update tracking fields
        unit.exchange_rate = self._exchange_rates.get(currency)
        unit.exchange_rate_date = datetime.now(timezone.utc)
        unit.last_price_update = datetime.now(timezone.utc)
        unit.price_version_id = price_version_id
        unit.requires_review = True
        
        await self.db.flush()
    
    async def _create_price_history(
        self,
        unit: Unit,
        new_price: Optional[float],
        new_price_usd: Optional[float],
        new_status: Optional[str],
        price_version_id: int,
        currency: str
    ):
        """Create price history record for a unit."""
        
        old_price = unit.price
        old_price_usd = unit.price_usd
        old_status = unit.status.value if unit.status else None
        
        # Determine change type
        if old_price and new_price:
            if new_price > old_price:
                change_type = 'increase'
            elif new_price < old_price:
                change_type = 'decrease'
            else:
                change_type = 'unchanged'
        elif old_status != new_status:
            change_type = 'status_change'
        else:
            change_type = 'update'
        
        # Calculate changes
        price_change = (new_price - old_price) if (old_price and new_price) else None
        price_change_percent = self._calculate_change_percent(old_price, new_price)
        
        # Calculate price per sqm
        old_price_per_sqm = unit.price_per_sqm
        new_price_per_sqm = (new_price / unit.area_sqm) if (new_price and unit.area_sqm) else None
        
        history = PriceHistory(
            unit_id=unit.id,
            price_version_id=price_version_id,
            old_price=old_price,
            old_price_usd=old_price_usd,
            old_price_per_sqm=old_price_per_sqm,
            old_status=old_status,
            new_price=new_price,
            new_price_usd=new_price_usd,
            new_price_per_sqm=new_price_per_sqm,
            new_status=new_status,
            price_change=price_change,
            price_change_percent=price_change_percent,
            change_type=change_type,
            currency=currency,
            exchange_rate=self._exchange_rates.get(currency)
        )
        
        self.db.add(history)
        await self.db.flush()
    
    def _price_changed(self, existing: Unit, parsed: ParsedUnit, currency: str) -> bool:
        """Check if price changed."""
        if parsed.price is None:
            return False
        if existing.price is None:
            return True
        
        # Allow for small rounding differences (0.01%)
        threshold = abs(existing.price * 0.0001)
        return abs(existing.price - parsed.price) > threshold
    
    def _details_changed(self, existing: Unit, parsed: ParsedUnit) -> bool:
        """Check if non-price details changed."""
        if parsed.area_sqm and existing.area_sqm != parsed.area_sqm:
            return True
        if parsed.floor and existing.floor != parsed.floor:
            return True
        if parsed.bedrooms is not None and existing.bedrooms != parsed.bedrooms:
            return True
        if parsed.bathrooms is not None and existing.bathrooms != parsed.bathrooms:
            return True
        return False
    
    def _status_changed(self, existing: Unit, parsed: ParsedUnit) -> bool:
        """Check if status changed."""
        if parsed.status == ParsedUnitStatus.UNKNOWN:
            return False
        
        mapped_status = self._map_unit_status(parsed.status)
        return existing.status != mapped_status
    
    def _calculate_change_percent(
        self, 
        old_price: Optional[float], 
        new_price: Optional[float]
    ) -> Optional[float]:
        """Calculate percentage change."""
        if not old_price or not new_price or old_price == 0:
            return None
        return round(((new_price - old_price) / old_price) * 100, 2)
    
    def _convert_to_usd(self, amount: Optional[float], currency: str) -> Optional[float]:
        """Convert amount to USD."""
        if amount is None:
            return None
        
        rate = self._exchange_rates.get(currency, self.DEFAULT_EXCHANGE_RATES.get(currency, 1.0))
        return round(amount * rate, 2)
    
    async def _load_exchange_rate(self, currency: str):
        """Load exchange rate from database or use default."""
        if currency == 'USD':
            self._exchange_rates['USD'] = 1.0
            return
        
        # Try to get from database
        result = await self.db.execute(
            select(ExchangeRate)
            .where(
                ExchangeRate.base_currency == currency,
                ExchangeRate.target_currency == 'USD'
            )
            .order_by(ExchangeRate.rate_date.desc())
            .limit(1)
        )
        rate = result.scalar_one_or_none()
        
        if rate:
            self._exchange_rates[currency] = rate.rate
        else:
            # Use default
            self._exchange_rates[currency] = self.DEFAULT_EXCHANGE_RATES.get(currency, 0.028)
            logger.warning(f"Using default exchange rate for {currency}")
    
    def _determine_unit_type(self, bedrooms: Optional[int]) -> UnitType:
        """Determine UnitType enum from bedroom count."""
        if bedrooms is None or bedrooms == 0:
            return UnitType.STUDIO
        
        mapping = {
            1: UnitType.ONE_BR,
            2: UnitType.TWO_BR,
            3: UnitType.THREE_BR,
            4: UnitType.FOUR_BR,
            5: UnitType.FIVE_BR,
            6: UnitType.SIX_BR,
            7: UnitType.SEVEN_BR,
            8: UnitType.EIGHT_BR,
            9: UnitType.NINE_BR,
            10: UnitType.TEN_BR,
        }
        
        return mapping.get(bedrooms, UnitType.TEN_BR)
    
    def _map_unit_status(self, parsed_status: ParsedUnitStatus) -> UnitStatus:
        """Map parsed status to Unit status enum."""
        mapping = {
            ParsedUnitStatus.AVAILABLE: UnitStatus.AVAILABLE,
            ParsedUnitStatus.RESERVED: UnitStatus.RESERVED,
            ParsedUnitStatus.SOLD: UnitStatus.SOLD,
            ParsedUnitStatus.HOLD: UnitStatus.RESERVED,
            ParsedUnitStatus.UNKNOWN: UnitStatus.AVAILABLE,  # Default to available
        }
        return mapping.get(parsed_status, UnitStatus.AVAILABLE)
    
    def _map_view_type(self, view_str: Optional[str]) -> Optional[ViewType]:
        """Map view string to ViewType enum."""
        if not view_str:
            return None
        
        view_lower = view_str.lower()
        
        if 'sea' in view_lower or 'ocean' in view_lower:
            return ViewType.SEA
        if 'pool' in view_lower:
            return ViewType.POOL
        if 'garden' in view_lower:
            return ViewType.GARDEN
        if 'mountain' in view_lower or 'hill' in view_lower:
            return ViewType.MOUNTAIN
        if 'city' in view_lower or 'urban' in view_lower:
            return ViewType.CITY
        if 'park' in view_lower:
            return ViewType.PARK
        if 'golf' in view_lower:
            return ViewType.GOLF
        if 'lake' in view_lower:
            return ViewType.LAKE
        if 'river' in view_lower:
            return ViewType.RIVER
        
        return ViewType.NONE


async def ingest_price_data(
    db: AsyncSession,
    project_id: int,
    price_version_id: int,
    parsed_data: ParsedPriceData,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function for ingesting price data.
    
    Args:
        db: Database session
        project_id: Project ID
        price_version_id: PriceVersion ID
        parsed_data: Parsed price data
        user_id: User performing ingestion
        
    Returns:
        Ingestion result
    """
    service = PriceIngestionService(db)
    return await service.ingest(project_id, price_version_id, parsed_data, user_id)
