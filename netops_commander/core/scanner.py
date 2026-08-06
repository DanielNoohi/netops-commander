"""
Async background workers for network operations.
Provides scan scheduling, device persistence, and export functionality.
"""

import asyncio
import ipaddress
import json
from datetime import datetime, timezone
from typing import Callable, Optional, List

from .discovery import discover_host, DiscoveredDevice
from ..database.database import session_scope
from ..database.models import Device as DeviceModel, ScanHistory
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
    scan_mgr: Optional[CancellableScan] = None,
) -> List[DiscoveredDevice]:
    """
    Scan all IPs in CIDR range.

    Args:
        cidr: CIDR notation (e.g., '192.168.1.0/24')
        progress_callback: Callable(ip, count, total) for progress updates
        scan_mgr: Optional CancellableScan for cancellation support

    Returns:
        List of DiscoveredDevice objects
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = list(network.hosts())
        # /31 and /32 have empty .hosts(); still probe the address(es)
        if not hosts:
            hosts = list(network)
        total = len(hosts)
    except ValueError as e:
        log.error(f"Invalid CIDR '{cidr}': {e}")
        return []

    if scan_mgr is None:
        scan_mgr = CancellableScan()
    config = get_config()
    # Windows Proactor cannot sustain huge concurrent ping subprocesses
    import platform
    default_conc = 32 if platform.system().lower() == "windows" else 128
    concurrency = int(config.get("app.scan_concurrency", default_conc))
    if platform.system().lower() == "windows":
        concurrency = min(concurrency, 48)
    timeout = float(config.get("app.scan_timeout", 2.0))
    devices: List[DiscoveredDevice] = []

    async def process_host(ip_str: str, idx: int):
        if not scan_mgr.can_continue():
            return None
        try:
            device = await discover_host(
                ip_str,
                ping_timeout=timeout,
            )
        except Exception as e:
            log.debug("discover_host failed for %s: %s", ip_str, e)
            return None
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

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            log.debug(f"Scan task error: {result}")
            continue
        if result and result.online:
            devices.append(result)

    log.info("scan_cidr %s finished: %s online / %s probed", cidr, len(devices), total)
    return devices


async def background_scan(
    cidr: str,
    scan_mgr: CancellableScan,
    done_callback: Callable,
    error_callback: Callable,
    progress_callback: Optional[Callable] = None,
) -> None:
    """
    Start background scan that updates state via callbacks.

    Args:
        cidr: CIDR notation for scan range
        scan_mgr: CancellableScan instance to control lifecycle
        done_callback: Called with (devices_list) on completion
        error_callback: Called with (exception) on error
        progress_callback: Optional Callable(ip, count, total)
    """
    try:
        devices = await scan_cidr(
            cidr, progress_callback=progress_callback, scan_mgr=scan_mgr
        )
        done_callback(devices)
    except Exception as e:
        error_callback(e)
    finally:
        scan_mgr._cancel_event.set()


def persist_device(device: DiscoveredDevice) -> bool:
    """
    Persist discovered device to database.
    Returns False if device is offline (not persisted).

    Handles both new devices and updates to existing ones.
    New devices default to is_monitored=False (opt-in monitoring).
    """
    if not device.online:
        return False

    now = datetime.now(timezone.utc)
    config = get_config()
    # Support both key spellings used in config.yaml / defaults
    default_monitor_interval = config.get(
        "app.monitor_interval",
        config.get("app.monitoring_interval", 60),
    )

    ports_json = json.dumps(list(device.open_ports or []))

    with session_scope() as session:
        existing = session.query(DeviceModel).filter_by(ip_address=device.ip_address).first()
        if existing:
            existing.hostname = device.hostname or existing.hostname
            existing.mac_address = device.mac_address
            existing.vendor = device.vendor
            existing.latency_ms = device.latency_ms
            existing.open_ports = ports_json
            existing.device_type = device.device_type
            existing.online = True
            existing.last_seen = now
            existing.last_check = now
            existing.updated_at = now
            device_id = existing.id
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
                open_ports=ports_json,
                first_seen=now,
                last_seen=now,
                last_check=now,
                is_monitored=False,  # opt-in
                monitor_interval=default_monitor_interval,
            )
            session.add(new_dev)
            session.flush()  # assign PK for ScanHistory FK
            device_id = new_dev.id

        session.add(
            ScanHistory(
                device_id=device_id,
                scan_type=device.discovery_method or "ping",
                online=True,
                latency_ms=device.latency_ms,
                ports_found=ports_json,
                details=f"host={device.ip_address}",
                timestamp=now,
            )
        )
    return True
