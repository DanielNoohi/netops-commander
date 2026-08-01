"""
Async background workers for network operations.
Provides scan scheduling, device persistence, and export functionality.
"""

import asyncio
import csv
import json
import ipaddress
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable, Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from .discovery import discover_host, DiscoveredDevice
from ..database.database import session_scope
from ..database.models import Device as DeviceModel
from ..config import get_config
from ..utils.logger import get_logger


log = get_logger(__name__)


class CancellableScan:
    """Manage cancellable network scan operations."""

    def __init__(self):
        self._cancel_event = asyncio.Event()
        self._cancel_event.set()  # No cancellation by default

    def cancel(self) -> None:
        """Signal cancellation for all running tasks."""
        self._cancel_event.clear()

    def can_continue(self) -> bool:
        """Check if operation should continue."""
        return self._cancel_event.is_set()


async def scan_cidr(
    cidr: str,
    progress_callback: Optional[Callable] = None,
) -> List[DiscoveredDevice]:
    """
    Scan all IPs in CIDR range.

    Args:
        cidr: CIDR notation (e.g., '192.168.1.0/24')
        progress_callback: Callable(ip, count, total) for progress updates

    Returns:
        List of DiscoveredDevice objects
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = list(network.hosts())
        total = len(hosts)
    except ValueError as e:
        log.error(f"Invalid CIDR '{cidr}': {e}")
        return []

    scan_mgr = CancellableScan()
    config = get_config()
    concurrency = config.get("app.scan_concurrency", 128)
    timeout = config.get("app.scan_timeout", 2.0)
    devices: List[DiscoveredDevice] = []

    async def process_host(ip_str: str, idx: int):
        if not scan_mgr.can_continue():
            return None
        device = await discover_host(
            ip_str,
            ping_timeout=timeout,
        )
        if progress_callback:
            try:
                progress_callback(ip_str, idx, total)
            except Exception:
                pass
        return device

    semaphore = asyncio.Semaphore(concurrency)

    async def limited_process(ip_str: str, idx: int) -> Optional[DiscoveredDevice]:
        async with semaphore:
            return await process_host(ip_str, idx)

    tasks = [
        asyncio.create_task(limited_process(str(ip), i))
        for i, ip in enumerate(hosts)
    ]

    for coro in asyncio.as_completed(tasks, timeout=None):
        if not scan_mgr.can_continue():
            for t in tasks:
                if not t.done():
                    t.cancel()
            break
        try:
            result = await coro
            if result and result.online:
                devices.append(result)
        except (asyncio.CancelledError, Exception) as e:
            log.debug(f"Scan task error: {e}")

    return devices


async def background_scan(
    cidr: str,
    scan_mgr: CancellableScan,
    done_callback: Callable,
    error_callback: Callable,
) -> None:
    """
    Start background scan that updates state via callbacks.

    Args:
        cidr: CIDR notation for scan range
        scan_mgr: CancellableScan instance to control lifecycle
        done_callback: Called with (devices_list) on completion
        error_callback: Called with (exception) on error
    """

    async def _run():
        try:
            devices = await scan_cidr(cidr)
            done_callback(devices)
        except Exception as e:
            error_callback(e)

    asyncio.create_task(_run())
    scan_mgr._cancel_event.set()  # Mark as "ready to run" (event set = can continue)


def persist_device(device: DiscoveredDevice) -> bool:
    """
    Persist discovered device to database.
    Returns False if device is offline (not persisted).

    Handles both new devices and updates to existing ones.
    Sets is_monitored=True by default, monitor_interval from config.
    """
    if not device.online:
        return False

    now = datetime.now(timezone.utc)
    config = get_config()
    default_monitor_interval = config.get("app.monitor_interval", 60)

    with session_scope() as session:
        existing = session.query(DeviceModel).filter_by(ip_address=device.ip_address).first()
        if existing:
            existing.hostname = device.hostname or existing.hostname
            existing.mac_address = device.mac_address
            existing.vendor = device.vendor
            existing.latency_ms = device.latency_ms
            existing.open_ports = json.dumps(device.open_ports)
            existing.device_type = device.device_type
            existing.online = True
            existing.last_seen = now
            existing.last_check = now
            existing.updated_at = now
            # Preserve monitoring state if already tracked
        else:
            new_dev = DeviceModel(
                ip_address=device.ip_address,
                hostname=device.hostname,
                mac_address=device.mac_address,
                vendor=device.vendor,
                device_type=device.device_type,
                online=True,
                latency_ms=device.latency_ms,
                open_ports=json.dumps(device.open_ports),
                first_seen=now,
                last_seen=now,
                is_monitored=True,
                monitor_interval=default_monitor_interval,
            )
            session.add(new_dev)
    return True


def export_devices_csv(filename: str, devices: List[DiscoveredDevice]) -> None:
    """Export devices to CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ip_address", "hostname", "mac_address", "vendor", "device_type",
            "online", "latency_ms", "open_ports", "notes", "tags", "first_seen", "last_seen"
        ])
        for d in devices:
            writer.writerow([
                d.ip_address, d.hostname or "", d.mac_address or "", d.vendor or "",
                d.device_type or "", d.online, d.latency_ms or "", "|".join(map(str, d.open_ports)),
                d.notes or "", d.tags or "", d.first_seen.isoformat() if d.first_seen else "",
                d.last_seen.isoformat() if d.last_seen else ""
            ])


def export_devices_json(filename: str, devices: List[DiscoveredDevice]) -> None:
    """Export devices to JSON file."""
    data = [asdict(d) for d in devices]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)