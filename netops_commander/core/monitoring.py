"""Monitoring controller and alert generation."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Callable

from .discovery import async_ping
from .alerts import severity_for
from ..database.database import session_scope
from ..database.models import Device, MonitorResult, Alert
from ..config import get_config
from ..utils.logger import get_logger

log = get_logger(__name__)

# Latency threshold (ms) for high_latency alerts
HIGH_LATENCY_MS = 200.0


class MonitorController:
    """Poll monitored devices on an interval and write MonitorResult + Alert rows."""

    def __init__(self, interval: Optional[int] = None):
        cfg = get_config()
        self.interval = interval or int(
            cfg.get("app.monitoring_interval", cfg.get("app.monitor_interval", 60))
        )
        self.devices: Dict[int, str] = {}
        self._task: Optional[asyncio.Task] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._prev_online: Dict[int, bool] = {}
        self._prev_high_latency: Dict[int, bool] = {}
        # Optional UI hook: alert_callback(severity, message, device_id?)
        self.alert_callback: Optional[Callable] = None
        self._max_devices = int(cfg.get("app.monitor_max_devices", 25))

    def add_device(self, device_id: int, ip: str) -> None:
        if len(self.devices) >= self._max_devices and device_id not in self.devices:
            log.warning(
                "Monitor max devices (%s) reached; not adding %s",
                self._max_devices,
                ip,
            )
            return
        self.devices[device_id] = ip

    def remove_device(self, device_id: int) -> None:
        self.devices.pop(device_id, None)
        self._prev_online.pop(device_id, None)
        self._prev_high_latency.pop(device_id, None)

    def load_from_db(self) -> int:
        """Load all is_monitored devices from SQLite. Returns count loaded."""
        self.devices.clear()
        self._prev_high_latency.clear()
        with session_scope() as session:
            rows = (
                session.query(Device)
                .filter(Device.is_monitored.is_(True))
                .limit(self._max_devices)
                .all()
            )
            for d in rows:
                self.devices[d.id] = d.ip_address
                self._prev_online[d.id] = bool(d.online)
        return len(self.devices)

    def sync_device(self, device_id: int, ip: str, monitored: bool) -> None:
        if monitored:
            self.add_device(device_id, ip)
        else:
            self.remove_device(device_id)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def run_forever(self, loop: asyncio.AbstractEventLoop) -> None:
        """Run the monitor loop on ``loop`` until cancelled (blocking).

        Used by ``MonitorThread`` which owns a dedicated event loop. The task
        is stored on the controller so ``stop()`` (invoked from the GUI thread)
        can cancel it scheduler-safely via ``loop.call_soon_threadsafe``.
        """
        self._event_loop = loop
        self._task = loop.create_task(self._loop())
        try:
            loop.run_until_complete(self._task)
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            self._event_loop = None

    def stop(self) -> None:
        """Stop the monitor loop.

        Works whether driven via ``start()`` (same event loop) or via a
        ``MonitorThread`` (separate loop in another thread): the active task
        is cancelled scheduler-safe from whatever thread invokes this.
        """
        task = self._task
        loop = self._event_loop
        if task is not None and not task.done():
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(task.cancel)
            else:
                task.cancel()
        self._task = None
        self._event_loop = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def _loop(self):
        while True:
            try:
                await self._run_pass()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.interval)

    async def _run_pass(self):
        for device_id, ip in list(self.devices.items()):
            try:
                online, latency = await async_ping(ip, timeout=2.0)
            except Exception as e:
                log.debug("Ping failed for %s: %s", ip, e)
                online, latency = False, None
            loss = 0.0 if online else 100.0
            now = datetime.now(timezone.utc)
            prev = self._prev_online.get(device_id)

            with session_scope() as session:
                mr = MonitorResult(
                    device_id=device_id,
                    online=online,
                    latency_ms=latency,
                    packet_loss_pct=loss,
                )
                session.add(mr)
                dev = session.get(Device, device_id)
                hostname = ""
                if dev:
                    dev.online = online
                    dev.latency_ms = latency
                    dev.last_check = now
                    if online:
                        dev.last_seen = now
                    hostname = dev.hostname or dev.ip_address

                # State-transition alerts (edge-triggered to avoid spam)
                if prev is True and not online:
                    create_alert(
                        session,
                        "offline",
                        f"{hostname or ip} went offline",
                        device_id=device_id,
                        severity=severity_for("offline"),
                    )
                    self._emit("critical", f"{ip} offline", device_id)
                elif prev is False and online:
                    create_alert(
                        session,
                        "recovery",
                        f"{hostname or ip} recovered",
                        device_id=device_id,
                        severity=severity_for("recovery"),
                    )
                    self._emit("info", f"{ip} recovered", device_id)

                high_now = bool(
                    online and latency is not None and latency >= HIGH_LATENCY_MS
                )
                was_high = self._prev_high_latency.get(device_id, False)
                if high_now and not was_high:
                    create_alert(
                        session,
                        "high_latency",
                        f"{hostname or ip} latency {latency:.0f} ms",
                        device_id=device_id,
                        severity=severity_for("high_latency"),
                    )
                    self._emit(
                        "warning",
                        f"{ip} high latency {latency:.0f}ms",
                        device_id,
                    )
                self._prev_high_latency[device_id] = high_now

            self._prev_online[device_id] = online

    def _emit(self, severity: str, message: str, device_id: Optional[int] = None) -> None:
        if self.alert_callback:
            try:
                self.alert_callback(severity, message, device_id)
            except TypeError:
                # Older 2-arg callback
                try:
                    self.alert_callback(severity, message)
                except Exception:
                    pass
            except Exception as e:
                log.debug("alert_callback error: %s", e)


def create_alert(
    session,
    alert_type: str,
    message: str,
    device_id: Optional[int] = None,
    severity: str = "info",
) -> None:
    alert = Alert(
        alert_type=alert_type,
        message=message,
        severity=severity or severity_for(alert_type),
        device_id=device_id,
        timestamp=datetime.now(timezone.utc),
    )
    session.add(alert)
