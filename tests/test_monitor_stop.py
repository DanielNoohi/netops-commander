"""Quick sanity test: MonitorController.stop() must terminate run_forever() promptly."""
import asyncio
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netops_commander.config import get_config
from netops_commander.database.database import init_database
from netops_commander.core.monitoring import MonitorController

# Point the DB at a throwaway file so the controller loop can persist results
# (its probe pass does INSERTs) without touching any real database.
_tmpdir = tempfile.mkdtemp(prefix="netops_test_")
# Mutate the singleton config directly; calling set() would persist to the
# repo's config.yaml, which a test must never do.
get_config()._config["app"]["database_path"] = os.path.join(_tmpdir, "monitor_stop.db")
init_database()

from netops_commander.database.database import session_scope
from netops_commander.database.models import Device

with session_scope() as s:
    s.add(Device(id=1, ip_address="127.0.0.1", online=True))


def test_stop_from_other_thread():
    ctl = MonitorController(interval=60)  # long interval; loop idles in sleep
    ctl.add_device(1, "127.0.0.1")

    result = {}

    def drive():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ctl.run_forever(loop)
        finally:
            loop.close()
        result["thread_exited"] = True

    t = threading.Thread(target=drive, daemon=True)
    t.start()
    time.sleep(1.0)
    assert ctl.running is True, f"expected running=True, got {ctl.running}"
    ctl.stop()  # called from main thread, like the GUI does
    t.join(timeout=5)
    assert not t.is_alive(), "FAIL: monitor thread did not exit after stop()"
    assert result.get("thread_exited"), "FAIL: run_forever did not return"
    assert ctl.running is False
    print("PASS: stop() from another thread terminates the monitor loop promptly")


if __name__ == "__main__":
    test_stop_from_other_thread()