"""
Monitoring and Logging Module

Provides comprehensive logging, metrics tracking, and monitoring for the
email classification system.

Features:
- Classification metrics (layer usage, confidence, processing time)
- Performance tracking (latency, throughput)
- Error logging and alerts
- Daily reports and statistics
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path

from sqlalchemy.orm import Session
from agent_platform.db.database import get_db


@dataclass
class ClassificationMetrics:
    """Metrics for a single email classification."""
    email_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    layer_used: str = ""
    category: str = ""
    confidence: float = 0.0
    importance: float = 0.0
    llm_provider: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class BatchMetrics:
    """Aggregated metrics for a batch of classifications."""
    batch_id: str
    account_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_processed: int = 0
    total_time_ms: float = 0.0

    # By layer
    by_layer: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # By category
    by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # By confidence
    high_confidence: int = 0  # >= 0.85
    medium_confidence: int = 0  # 0.6-0.85
    low_confidence: int = 0  # < 0.6

    # Errors
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)

    @property
    def avg_processing_time_ms(self) -> float:
        """Average processing time per email."""
        if self.total_processed == 0:
            return 0.0
        return self.total_time_ms / self.total_processed

    @property
    def throughput_per_second(self) -> float:
        """Emails processed per second."""
        if self.total_time_ms == 0:
            return 0.0
        return (self.total_processed / (self.total_time_ms / 1000.0))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['by_layer'] = dict(self.by_layer)
        data['by_category'] = dict(self.by_category)
        data['avg_processing_time_ms'] = self.avg_processing_time_ms
        data['throughput_per_second'] = self.throughput_per_second
        return data


class MetricsCollector:
    """Collect and aggregate classification metrics."""

    def __init__(self):
        """Initialize collector."""
        self.metrics: List[ClassificationMetrics] = []
        self.batch_metrics: Dict[str, BatchMetrics] = {}
        self.current_batch: Optional[BatchMetrics] = None

    def start_batch(self, batch_id: str, account_id: str) -> None:
        """Start a new batch."""
        self.current_batch = BatchMetrics(
            batch_id=batch_id,
            account_id=account_id,
        )

    def record_classification(
        self,
        email_id: str,
        processing_time_ms: float,
        layer_used: str,
        category: str,
        confidence: float,
        importance: float,
        llm_provider: str = "",
        error: Optional[str] = None,
    ) -> None:
        """Record a single classification."""
        metric = ClassificationMetrics(
            email_id=email_id,
            processing_time_ms=processing_time_ms,
            layer_used=layer_used,
            category=category,
            confidence=confidence,
            importance=importance,
            llm_provider=llm_provider,
            error=error,
        )

        self.metrics.append(metric)

        if self.current_batch:
            self.current_batch.total_processed += 1
            self.current_batch.total_time_ms += processing_time_ms
            self.current_batch.by_layer[layer_used] += 1
            self.current_batch.by_category[category] += 1

            if confidence >= 0.85:
                self.current_batch.high_confidence += 1
            elif confidence >= 0.60:
                self.current_batch.medium_confidence += 1
            else:
                self.current_batch.low_confidence += 1

            if error:
                self.current_batch.errors += 1
                self.current_batch.error_messages.append(error)

    def end_batch(self) -> Optional[BatchMetrics]:
        """End current batch and return metrics."""
        if not self.current_batch:
            return None

        batch = self.current_batch
        self.batch_metrics[batch.batch_id] = batch
        self.current_batch = None
        return batch

    def get_batch_summary(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific batch."""
        batch = self.batch_metrics.get(batch_id)
        if not batch:
            return None
        return batch.to_dict()

    def get_recent_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get summary of recent classifications."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent = [m for m in self.metrics if m.timestamp > cutoff]

        if not recent:
            return {
                'period_minutes': minutes,
                'total_classified': 0,
                'avg_processing_time_ms': 0,
            }

        total_time = sum(m.processing_time_ms for m in recent)
        by_layer = defaultdict(int)
        by_category = defaultdict(int)
        high_conf = sum(1 for m in recent if m.confidence >= 0.85)
        medium_conf = sum(1 for m in recent if 0.60 <= m.confidence < 0.85)
        low_conf = sum(1 for m in recent if m.confidence < 0.60)

        for m in recent:
            by_layer[m.layer_used] += 1
            by_category[m.category] += 1

        return {
            'period_minutes': minutes,
            'total_classified': len(recent),
            'avg_processing_time_ms': total_time / len(recent) if recent else 0,
            'by_layer': dict(by_layer),
            'by_category': dict(by_category),
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
        }


class SystemLogger:
    """System-wide logging configuration."""

    _logger = None

    @classmethod
    def configure(cls, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
        """Configure logging."""
        if cls._logger:
            return cls._logger

        logger = logging.getLogger('agent_platform')
        logger.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler (if log_file specified)
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        cls._logger = logger
        return logger

    @classmethod
    def get_logger(cls, name: str = 'agent_platform') -> logging.Logger:
        """Get logger instance."""
        if not cls._logger:
            cls.configure()
        return logging.getLogger(name)


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics_collector


def log_classification(
    email_id: str,
    processing_time_ms: float,
    layer_used: str,
    category: str,
    confidence: float,
    importance: float,
    llm_provider: str = "",
) -> None:
    """Log a classification event."""
    logger = SystemLogger.get_logger()
    logger.info(
        f"Classified {email_id}: {category} "
        f"(confidence={confidence:.2f}, layer={layer_used}, time={processing_time_ms:.0f}ms)"
    )

    # Record in metrics
    _metrics_collector.record_classification(
        email_id=email_id,
        processing_time_ms=processing_time_ms,
        layer_used=layer_used,
        category=category,
        confidence=confidence,
        importance=importance,
        llm_provider=llm_provider,
    )


def log_error(message: str, exception: Optional[Exception] = None) -> None:
    """Log an error."""
    logger = SystemLogger.get_logger()
    if exception:
        logger.error(message, exc_info=exception)
    else:
        logger.error(message)


def create_daily_report(db: Session, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Create daily report of classification statistics.

    Args:
        db: Database session
        output_file: Optional file to write report to

    Returns:
        Report dictionary
    """
    from agent_platform.db.models import ProcessedEmail, FeedbackEvent

    yesterday = datetime.utcnow() - timedelta(days=1)

    # Query yesterday's classifications
    processed = db.query(ProcessedEmail).filter(
        ProcessedEmail.processed_at >= yesterday
    ).all()

    # Query yesterday's feedback
    feedback = db.query(FeedbackEvent).filter(
        FeedbackEvent.created_at >= yesterday
    ).all()

    # Build report
    report = {
        'date': yesterday.date().isoformat(),
        'total_classified': len(processed),
        'total_feedback_events': len(feedback),
        'by_category': defaultdict(int),
        'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
        'by_account': defaultdict(int),
    }

    for p in processed:
        report['by_category'][p.category] += 1
        report['by_account'][p.account_id] += 1

        if p.classification_confidence >= 0.85:
            report['by_confidence']['high'] += 1
        elif p.classification_confidence >= 0.60:
            report['by_confidence']['medium'] += 1
        else:
            report['by_confidence']['low'] += 1

    # Write to file if specified
    if output_file:
        import json
        output_file_path = Path(output_file)
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file_path, 'w') as f:
            # Convert defaultdict to dict for JSON serialization
            report_json = {
                **report,
                'by_category': dict(report['by_category']),
                'by_account': dict(report['by_account']),
            }
            json.dump(report_json, f, indent=2, default=str)

    return report
