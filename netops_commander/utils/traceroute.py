"""Traceroute / tracert runner (no shell=True)."""
from __future__ import annotations

import platform
import subprocess
from typing import Callable, List, Optional


def build_traceroute_cmd(host: str, max_hops: int = 30) -> List[str]:
    system = platform.system().lower()
    if system == "windows":
        return ["tracert", "-d", "-h", str(max_hops), host]
    # Prefer traceroute; fall back to tracepath if needed by caller
    return ["traceroute", "-n", "-m", str(max_hops), host]


def run_traceroute(
    host: str,
    max_hops: int = 30,
    timeout: float = 120.0,
    line_callback: Optional[Callable[[str], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> int:
    """
    Run traceroute and stream lines to callback.
    Returns process return code (or -1 on failure to start).
    """
    cmd = build_traceroute_cmd(host, max_hops=max_hops)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        if platform.system().lower() != "windows":
            # try tracepath
            try:
                proc = subprocess.Popen(
                    ["tracepath", "-n", host],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except FileNotFoundError:
                if line_callback:
                    line_callback("traceroute/tracepath not found on PATH")
                return -1
        else:
            if line_callback:
                line_callback("tracert not found on PATH")
            return -1

    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            if should_stop and should_stop():
                proc.terminate()
                break
            text = line.rstrip()
            if line_callback and text:
                line_callback(text)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            if line_callback:
                line_callback("traceroute timed out")
            return -1
    finally:
        if proc.poll() is None:
            proc.kill()
