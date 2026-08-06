"""Open common remote admin tools for a host (OS helpers, no shell=True)."""
from __future__ import annotations

import platform
import shutil
import subprocess
import webbrowser
from typing import Optional, Tuple
from urllib.parse import quote


def open_http(host: str, https: bool = True) -> Tuple[bool, str]:
    host = host.strip()
    if not host:
        return False, "Empty host"
    scheme = "https" if https else "http"
    url = f"{scheme}://{host}"
    try:
        webbrowser.open(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, str(e)


def open_rdp(host: str) -> Tuple[bool, str]:
    host = host.strip()
    if not host:
        return False, "Empty host"
    system = platform.system().lower()
    try:
        if system == "windows":
            subprocess.Popen(["mstsc", f"/v:{host}"])
            return True, f"Launching Remote Desktop → {host}"
        # FreeRDP if present
        if shutil.which("xfreerdp"):
            subprocess.Popen(["xfreerdp", f"/v:{host}"])
            return True, f"Launching xfreerdp → {host}"
        if shutil.which("open"):
            # macOS Screen Sharing style
            subprocess.Popen(["open", f"rdp://{host}"])
            return True, f"Opening rdp://{host}"
        return False, "No RDP client found (mstsc / xfreerdp)"
    except Exception as e:
        return False, str(e)


def open_ssh(host: str, user: Optional[str] = None) -> Tuple[bool, str]:
    host = host.strip()
    if not host:
        return False, "Empty host"
    target = f"{user}@{host}" if user else host
    system = platform.system().lower()
    try:
        if system == "windows":
            # Prefer Windows Terminal, then ssh in console
            if shutil.which("wt"):
                subprocess.Popen(["wt", "ssh", target])
                return True, f"SSH via Windows Terminal → {target}"
            subprocess.Popen(["cmd", "/c", "start", "ssh", target])
            return True, f"SSH → {target}"
        terminal = None
        for cand in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            if shutil.which(cand):
                terminal = cand
                break
        if terminal == "gnome-terminal":
            subprocess.Popen([terminal, "--", "ssh", target])
        elif terminal:
            subprocess.Popen([terminal, "-e", "ssh", target])
        elif shutil.which("ssh"):
            subprocess.Popen(["ssh", target])
        else:
            return False, "ssh client not found"
        return True, f"SSH → {target}"
    except Exception as e:
        return False, str(e)


def open_vnc(host: str, port: int = 5900) -> Tuple[bool, str]:
    host = host.strip()
    if not host:
        return False, "Empty host"
    url = f"vnc://{host}:{port}"
    try:
        if platform.system().lower() == "darwin":
            subprocess.Popen(["open", url])
            return True, f"Opened {url}"
        # Fallback: browser won't help; try webbrowser for custom handlers
        webbrowser.open(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, str(e)


def mailto_host(host: str) -> Tuple[bool, str]:
    """Tiny helper kept for completeness / tests."""
    try:
        webbrowser.open(f"mailto:admin@{quote(host)}")
        return True, "Opened mail client"
    except Exception as e:
        return False, str(e)
