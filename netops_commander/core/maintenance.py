"""Periodic DB cleanup (history / monitor / alert retention)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

from ..config import get_config
from ..database.database import session_scope
from ..database.models import Alert, MonitorResult, ScanHistory
from ..utils.logger import get_logger

log = get_logger(__name__)


def purge_old_history(days: int | None = None) -> Dict[str, int]:
    """
    Delete scan/monitor/alert rows older than retention days.

    Returns counts deleted per table. No-op when days <= 0.
    """
    if days is None:
        days = int(get_config().get("app.history_retention_days", 30))
    if days <= 0:
        return {"scan_history": 0, "monitor_results": 0, "alerts": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts = {"scan_history": 0, "monitor_results": 0, "alerts": 0}
    with session_scope() as session:
        counts["scan_history"] = (
            session.query(ScanHistory)
            .filter(ScanHistory.timestamp < cutoff)
            .delete(synchronize_session=False)
        )
        counts["monitor_results"] = (
            session.query(MonitorResult)
            .filter(MonitorResult.timestamp < cutoff)
            .delete(synchronize_session=False)
        )
        counts["alerts"] = (
            session.query(Alert)
            .filter(Alert.timestamp < cutoff)
            .delete(synchronize_session=False)
        )
    total = sum(counts.values())
    if total:
        log.info(
            "Retention purge (%sd): scan=%s monitor=%s alerts=%s",
            days,
            counts["scan_history"],
            counts["monitor_results"],
            counts["alerts"],
        )
    return counts
