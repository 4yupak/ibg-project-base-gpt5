"""
Feedback Store - Stores and uses user feedback to improve column detection.
Implements a simple learning mechanism based on header pattern recognition.
"""
import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ColumnFeedback:
    """Single feedback entry for a column mapping."""
    header_text: str           # Original header text from file
    header_normalized: str     # Normalized version for matching
    suggested_field: str       # What the parser suggested
    correct_field: str         # What the user confirmed/corrected
    approved: bool             # True = user approved, False = user corrected
    file_type: str             # excel, pdf, google_sheets
    file_name: Optional[str] = None  # Original filename
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ColumnFeedback':
        return cls(**data)


@dataclass
class LearningPattern:
    """Learned pattern for column detection."""
    header_pattern: str        # Normalized header pattern
    field: str                 # Target field name
    confidence: float          # Base confidence score
    success_count: int = 0     # Number of times this worked
    failure_count: int = 0     # Number of times this was wrong
    last_used: Optional[str] = None
    
    @property
    def accuracy(self) -> float:
        """Calculate accuracy of this pattern."""
        total = self.success_count + self.failure_count
        if total == 0:
            return self.confidence
        return self.success_count / total
    
    @property
    def effective_confidence(self) -> float:
        """Confidence adjusted by usage history."""
        total = self.success_count + self.failure_count
        if total < 3:
            return self.confidence
        return self.accuracy * 0.7 + self.confidence * 0.3


class FeedbackStore:
    """
    Stores and utilizes user feedback to improve column detection accuracy.
    
    Features:
    - Exact pattern matching from user feedback
    - Fuzzy matching for partial matches
    - Base rules as fallback
    - Pattern learning from corrections
    - Persistence to JSON file
    """
    
    # Base column mappings (fallback rules)
    BASE_RULES = {
        'unit_number': [
            'unit', 'unit_number', 'unit no', 'unit #', 'no', 'номер', 
            'юнит', 'room', 'room no', 'unit id', '№', 'number', 'apartment',
            'apt', 'квартира', 'condo'
        ],
        'bedrooms': [
            'bedrooms', 'bedroom', 'br', 'bed', 'type', 'спальни', 
            'спален', 'комнат', 'beds', 'room type'
        ],
        'bathrooms': [
            'bathrooms', 'bathroom', 'bath', 'baths', 'ванные', 'санузел'
        ],
        'area': [
            'area', 'size', 'sqm', 'sq.m', 'площадь', 'm2', 'living area',
            'total area', 'area (sqm)', 'net area', 'gross area', 'sq m',
            'м2', 'square', 's общая', 'общая'
        ],
        'floor': [
            'floor', 'flr', 'этаж', 'level', 'storey', 'fl', 'этаже'
        ],
        'building': [
            'building', 'tower', 'block', 'здание', 'корпус', 'bldg',
            'секция', 'section'
        ],
        'price': [
            'price', 'total price', 'цена', 'стоимость', 'amount',
            'sale price', 'selling price', 'price (thb)', 'price (usd)',
            'cost', 'leasehold', 'freehold', 'apartment price', 'unit price',
            'стоимость тыс', 'thb', 'usd'
        ],
        'price_per_sqm': [
            'price per sqm', 'price/sqm', 'per sqm', 'sqm price', 
            'стоимость м2', 'цена за м2', 'price per m2', '$/sqm', 
            'thb/sqm', 'price/m2'
        ],
        'status': [
            'status', 'availability', 'статус', 'available', 'state',
            'avail', 'состояние', 'booking status', 'продано'
        ],
        'view': [
            'view', 'вид', 'view type', 'facing', 'orientation',
            'направ', 'ambience'
        ],
        'layout': [
            'layout', 'type', 'unit type', 'планировка', 'тип', 'plan',
            'layout type'
        ],
        'phase': [
            'phase', 'фаза', 'stage', 'этап', 'batch'
        ],
    }
    
    # Confidence levels
    EXACT_MATCH_CONFIDENCE = 1.0
    LEARNED_PATTERN_CONFIDENCE = 0.9
    PARTIAL_MATCH_CONFIDENCE = 0.7
    BASE_RULE_CONFIDENCE = 0.5
    FUZZY_MATCH_CONFIDENCE = 0.4
    UNKNOWN_CONFIDENCE = 0.1
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize feedback store.
        
        Args:
            storage_path: Path to JSON file for persistence.
                         Defaults to parser_feedback.json in current directory.
        """
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), 'parser_feedback.json'
        )
        
        # Learned patterns: normalized_header -> LearningPattern
        self.patterns: Dict[str, LearningPattern] = {}
        
        # Feedback history (for analysis)
        self.feedbacks: List[ColumnFeedback] = []
        
        # Statistics
        self.stats = {
            'total_feedbacks': 0,
            'approved_count': 0,
            'corrected_count': 0,
            'patterns_learned': 0,
        }
        
        self._load()
    
    def normalize(self, text: str) -> str:
        """Normalize text for pattern matching."""
        if not text:
            return ""
        # Lowercase, remove extra spaces, normalize separators
        text = str(text).lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('_', ' ').replace('-', ' ')
        return text
    
    def suggest_field(self, header: str) -> Tuple[str, float]:
        """
        Suggest a field mapping for a header.
        
        Args:
            header: Column header text
            
        Returns:
            Tuple of (field_name, confidence)
        """
        normalized = self.normalize(header)
        
        # 1. Exact match with learned patterns
        if normalized in self.patterns:
            pattern = self.patterns[normalized]
            confidence = pattern.effective_confidence
            logger.debug(f"Exact pattern match: '{header}' -> {pattern.field} ({confidence:.2f})")
            return pattern.field, min(confidence, self.EXACT_MATCH_CONFIDENCE)
        
        # 2. Partial match with learned patterns
        for pattern_key, pattern in self.patterns.items():
            if pattern_key in normalized or normalized in pattern_key:
                confidence = pattern.effective_confidence * 0.8
                logger.debug(f"Partial pattern match: '{header}' -> {pattern.field} ({confidence:.2f})")
                return pattern.field, min(confidence, self.LEARNED_PATTERN_CONFIDENCE)
        
        # 3. Base rules matching
        field, confidence = self._match_base_rules(normalized)
        if field != 'unknown':
            return field, confidence
        
        # 4. Fuzzy matching with patterns
        for pattern_key, pattern in self.patterns.items():
            similarity = self._calculate_similarity(normalized, pattern_key)
            if similarity > 0.6:
                confidence = pattern.effective_confidence * similarity * 0.7
                logger.debug(f"Fuzzy pattern match: '{header}' -> {pattern.field} ({confidence:.2f})")
                return pattern.field, min(confidence, self.FUZZY_MATCH_CONFIDENCE)
        
        return 'unknown', self.UNKNOWN_CONFIDENCE
    
    def _match_base_rules(self, normalized: str) -> Tuple[str, float]:
        """Match against base rules."""
        for field, keywords in self.BASE_RULES.items():
            for keyword in keywords:
                keyword_norm = self.normalize(keyword)
                # Exact keyword match
                if keyword_norm == normalized:
                    return field, self.BASE_RULE_CONFIDENCE + 0.2
                # Keyword contained in header
                if keyword_norm in normalized:
                    return field, self.BASE_RULE_CONFIDENCE
                # Header contained in keyword (for short headers)
                if len(normalized) >= 2 and normalized in keyword_norm:
                    return field, self.BASE_RULE_CONFIDENCE - 0.1
        
        return 'unknown', self.UNKNOWN_CONFIDENCE
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (simple Jaccard-like)."""
        if not s1 or not s2:
            return 0.0
        
        set1 = set(s1.split())
        set2 = set(s2.split())
        
        if not set1 or not set2:
            # Character-level similarity for short strings
            chars1 = set(s1)
            chars2 = set(s2)
            intersection = len(chars1 & chars2)
            union = len(chars1 | chars2)
            return intersection / union if union > 0 else 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def add_feedback(self, feedback: ColumnFeedback) -> None:
        """
        Add user feedback and update patterns.
        
        Args:
            feedback: ColumnFeedback instance
        """
        self.feedbacks.append(feedback)
        self.stats['total_feedbacks'] += 1
        
        if feedback.approved:
            self.stats['approved_count'] += 1
            # Reinforce the pattern
            self._reinforce_pattern(feedback.header_normalized, feedback.correct_field)
        else:
            self.stats['corrected_count'] += 1
            # User corrected - learn the new mapping
            self._learn_pattern(feedback.header_normalized, feedback.correct_field)
            # Penalize the wrong suggestion
            self._penalize_pattern(feedback.header_normalized, feedback.suggested_field)
        
        self._save()
        
        logger.info(
            f"Feedback added: '{feedback.header_text}' -> {feedback.correct_field} "
            f"(was: {feedback.suggested_field}, approved: {feedback.approved})"
        )
    
    def add_feedbacks_batch(self, feedbacks: List[ColumnFeedback]) -> None:
        """Add multiple feedbacks at once."""
        for feedback in feedbacks:
            self.add_feedback(feedback)
    
    def _learn_pattern(self, normalized_header: str, field: str) -> None:
        """Learn a new pattern from user correction."""
        if normalized_header in self.patterns:
            # Update existing pattern
            pattern = self.patterns[normalized_header]
            if pattern.field != field:
                # Field changed - this is a correction
                pattern.field = field
                pattern.success_count = 1
                pattern.failure_count = 0
            else:
                pattern.success_count += 1
        else:
            # Create new pattern
            self.patterns[normalized_header] = LearningPattern(
                header_pattern=normalized_header,
                field=field,
                confidence=self.LEARNED_PATTERN_CONFIDENCE,
                success_count=1,
                failure_count=0,
            )
            self.stats['patterns_learned'] += 1
        
        self.patterns[normalized_header].last_used = datetime.utcnow().isoformat()
    
    def _reinforce_pattern(self, normalized_header: str, field: str) -> None:
        """Reinforce an existing pattern (user approved)."""
        if normalized_header in self.patterns:
            pattern = self.patterns[normalized_header]
            if pattern.field == field:
                pattern.success_count += 1
        else:
            # Create pattern from approval
            self.patterns[normalized_header] = LearningPattern(
                header_pattern=normalized_header,
                field=field,
                confidence=self.LEARNED_PATTERN_CONFIDENCE,
                success_count=1,
                failure_count=0,
            )
            self.stats['patterns_learned'] += 1
    
    def _penalize_pattern(self, normalized_header: str, wrong_field: str) -> None:
        """Penalize a pattern for wrong suggestion."""
        # Find patterns that might have caused this
        for pattern_key, pattern in self.patterns.items():
            if pattern.field == wrong_field:
                if pattern_key == normalized_header or pattern_key in normalized_header:
                    pattern.failure_count += 1
    
    def suggest_all_columns(self, headers: List[str]) -> List[Dict]:
        """
        Suggest field mappings for all columns in a file.
        
        Args:
            headers: List of column header strings
            
        Returns:
            List of dicts with suggested mappings
        """
        suggestions = []
        used_fields = set()
        
        for idx, header in enumerate(headers):
            field, confidence = self.suggest_field(header)
            
            # Avoid duplicate field assignments
            if field != 'unknown' and field in used_fields:
                # Try to find alternative
                alt_field, alt_confidence = self._find_alternative(header, used_fields)
                if alt_confidence > self.UNKNOWN_CONFIDENCE:
                    field, confidence = alt_field, alt_confidence
                else:
                    confidence *= 0.5  # Reduce confidence for duplicates
            
            if field != 'unknown':
                used_fields.add(field)
            
            suggestions.append({
                'index': idx,
                'header': header,
                'header_normalized': self.normalize(header),
                'suggested_field': field,
                'confidence': round(confidence, 2),
            })
        
        return suggestions
    
    def _find_alternative(self, header: str, used_fields: set) -> Tuple[str, float]:
        """Find alternative field suggestion excluding used fields."""
        normalized = self.normalize(header)
        
        # Check base rules for alternatives
        for field, keywords in self.BASE_RULES.items():
            if field in used_fields:
                continue
            for keyword in keywords:
                if keyword in normalized or normalized in keyword:
                    return field, self.BASE_RULE_CONFIDENCE * 0.8
        
        return 'unknown', self.UNKNOWN_CONFIDENCE
    
    def get_stats(self) -> Dict:
        """Get learning statistics."""
        pattern_stats = {}
        for pattern in self.patterns.values():
            field = pattern.field
            if field not in pattern_stats:
                pattern_stats[field] = {
                    'patterns': 0,
                    'total_uses': 0,
                    'avg_accuracy': 0,
                }
            pattern_stats[field]['patterns'] += 1
            pattern_stats[field]['total_uses'] += pattern.success_count + pattern.failure_count
            pattern_stats[field]['avg_accuracy'] += pattern.accuracy
        
        # Calculate averages
        for field in pattern_stats:
            if pattern_stats[field]['patterns'] > 0:
                pattern_stats[field]['avg_accuracy'] /= pattern_stats[field]['patterns']
                pattern_stats[field]['avg_accuracy'] = round(pattern_stats[field]['avg_accuracy'], 2)
        
        return {
            'total_feedbacks': self.stats['total_feedbacks'],
            'approved_count': self.stats['approved_count'],
            'corrected_count': self.stats['corrected_count'],
            'patterns_learned': len(self.patterns),
            'accuracy_rate': round(
                self.stats['approved_count'] / max(1, self.stats['total_feedbacks']), 
                2
            ),
            'patterns_by_field': pattern_stats,
        }
    
    def _load(self) -> None:
        """Load patterns from storage."""
        if not os.path.exists(self.storage_path):
            logger.info(f"No feedback store found at {self.storage_path}, starting fresh")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load patterns
            for pattern_data in data.get('patterns', []):
                pattern = LearningPattern(**pattern_data)
                self.patterns[pattern.header_pattern] = pattern
            
            # Load stats
            self.stats = data.get('stats', self.stats)
            
            # Load recent feedbacks (keep last 100)
            for fb_data in data.get('feedbacks', [])[-100:]:
                self.feedbacks.append(ColumnFeedback.from_dict(fb_data))
            
            logger.info(f"Loaded {len(self.patterns)} patterns from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to load feedback store: {e}")
    
    def _save(self) -> None:
        """Save patterns to storage."""
        try:
            data = {
                'patterns': [
                    {
                        'header_pattern': p.header_pattern,
                        'field': p.field,
                        'confidence': p.confidence,
                        'success_count': p.success_count,
                        'failure_count': p.failure_count,
                        'last_used': p.last_used,
                    }
                    for p in self.patterns.values()
                ],
                'stats': self.stats,
                'feedbacks': [fb.to_dict() for fb in self.feedbacks[-100:]],  # Keep last 100
                'last_updated': datetime.utcnow().isoformat(),
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.patterns)} patterns to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save feedback store: {e}")
    
    def reset(self) -> None:
        """Reset all learned patterns (for testing)."""
        self.patterns = {}
        self.feedbacks = []
        self.stats = {
            'total_feedbacks': 0,
            'approved_count': 0,
            'corrected_count': 0,
            'patterns_learned': 0,
        }
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        logger.info("Feedback store reset")


# Singleton instance
_feedback_store: Optional[FeedbackStore] = None


def get_feedback_store() -> FeedbackStore:
    """Get or create singleton FeedbackStore instance."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store
