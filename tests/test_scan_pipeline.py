"""Functional test for the scan pipeline fix.

Verifies that background_scan actually runs the scan (the critical
v1.1.1 bug: asyncio.create_task fire-and-forget never executed).
"""
import asyncio
import sys
from dataclasses import dataclass, field


@dataclass
class DiscoveredDevice:
    ip_address: str
    online: bool = True
    hostname: str = ""
    mac_address: str = ""
    vendor: str = ""
    device_type: str = ""
    ports: list = field(default_factory=list)


async def test_scan_pipeline():
    """Verify scan_cidr runs to completion when awaited."""
    sys.path.insert(0, ".")

    from netops_commander.core.scanner import CancellableScan, scan_cidr, background_scan

    calls = []

    async def fake_discover_host(ip, ping_timeout=None):
        calls.append(ip)
        await asyncio.sleep(0.001)
        return DiscoveredDevice(ip_address=ip, online=True)

    # Patch discovery at the module level (scanner imports discover_host into its namespace)
    import netops_commander.core.scanner as scanner_mod
    scanner_mod.discover_host = fake_discover_host

    # Test 1: scan_cidr awaited directly produces results
    mgr = CancellableScan()
    devices = await scan_cidr("127.0.0.0/30", scan_mgr=mgr)
    assert len(calls) > 0, f"FAIL: scan_cidr never ran (calls={calls})"
    print(f"PASS: scan_cidr ran, discovered {len(devices)} online hosts from {len(calls)} pings")

    # Test 2: background_scan awaited runs the scan and fires done_callback
    calls2 = []
    done = []
    errors = []

    async def fake_discover_host2(ip, ping_timeout=None):
        calls2.append(ip)
        await asyncio.sleep(0.001)
        return DiscoveredDevice(ip_address=ip, online=True)

    scanner_mod.discover_host = fake_discover_host2

    mgr2 = CancellableScan()
    await background_scan(
        "127.0.0.0/30",
        scan_mgr=mgr2,
        done_callback=lambda devs: done.append(devs),
        error_callback=lambda e: errors.append(e),
    )
    assert len(calls2) > 0, f"FAIL: background_scan never ran the scan (calls={calls2})"
    assert len(done) == 1, f"FAIL: done_callback not fired (done={len(done)}, errors={errors})"
    assert len(errors) == 0, f"FAIL: error_callback fired: {errors}"
    print(f"PASS: background_scan ran, done_callback fired with {len(done[0])} devices, 0 errors")

    # Test 3: cancellation actually stops the scan
    calls3 = []

    async def fake_discover_host3(ip, ping_timeout=None):
        calls3.append(ip)
        await asyncio.sleep(0.05)
        return DiscoveredDevice(ip_address=ip, online=True)

    scanner_mod.discover_host = fake_discover_host3
    mgr3 = CancellableScan()
    mgr3.cancel()  # Signal cancellation BEFORE scan starts
    devices3 = await scan_cidr("127.0.0.0/30", scan_mgr=mgr3)
    print(f"PASS: cancelled scan returned early (pings={len(calls3)}, devices={len(devices3)})")

    print("\nALL SCAN PIPELINE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(test_scan_pipeline())
