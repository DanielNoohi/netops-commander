"""Route table and ARP table viewers (OS commands, no shell=True)."""
from __future__ import annotations

import platform
import subprocess
from typing import List, Tuple


def _run(cmd: List[str], timeout: float = 10.0) -> Tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as e:
        return -1, str(e)
    except subprocess.TimeoutExpired:
        return -1, "command timed out"
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return proc.returncode, out.strip()


def get_route_table() -> str:
    system = platform.system().lower()
    if system == "windows":
        code, text = _run(["route", "print"])
    else:
        code, text = _run(["ip", "route"])
        if code != 0 or not text:
            code, text = _run(["netstat", "-rn"])
    if code != 0 and not text:
        return f"Failed to read route table (exit {code})"
    return text


def get_arp_table() -> str:
    system = platform.system().lower()
    if system == "windows":
        code, text = _run(["arp", "-a"])
    else:
        code, text = _run(["ip", "neigh"])
        if code != 0 or not text:
            code, text = _run(["arp", "-n"])
    if code != 0 and not text:
        return f"Failed to read ARP table (exit {code})"
    return text
