"""Monitoring controller and alert generation."""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from .discovery import async_ping
from ..database.database import session_scope
from ..database.models import Device, MonitorResult, Alert
from ..utils.logger import get_logger

log = get_logger(__name__)


class MonitorController:
    def __init__(self, interval: int = 60):
        self.interval = interval
        self.devices: Dict[int, str] = {}
        self._task: Optional[asyncio.Task] = None
        self.alert_callback: Optional[Callable] = None

    def add_device(self, device_id: int, ip: str) -> None:
        self.devices[device_id] = ip

    def remove_device(self, device_id: int) -> None:
        self.devices.pop(device_id, None)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            try:
                await self._run_pass()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Monitor loop error: {e}")

    async def _run_pass(self):
        for device_id, ip in list(self.devices.items()):
            online, latency = await async_ping(ip, timeout=2.0)
            loss = 0.0 if online else 100.0
            with session_scope() as session:
                mr = MonitorResult(
                    device_id=device_id,
                    online=online,
                    latency_ms=latency,
                    packet_loss_pct=loss,
                )
                session.add(mr)
                dev = session.get(Device, device_id)
                if dev:
                    dev.online = online
                    dev.latency_ms = latency
                    dev.last_check = datetime.now(timezone.utc)
            if self.alert_callback:
                self.alert_callback("info", f"Checked {ip}: online={online} latency={latency}")


def create_alert(session, alert_type: str, message: str, device_id: Optional[int] = None, severity: str = "info") -> None:
    alert = Alert(
        alert_type=alert_type,
        message=message,
        severity=severity,
        device_id=device_id,
        timestamp=datetime.now(timezone.utc),
    )
    session.add(alert)