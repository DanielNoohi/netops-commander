"""Privilege detection."""
import os
import platform
import ctypes


def is_admin() -> bool:
    try:
        if platform.system().lower() == "windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False


def privilege_guidance() -> str:
    if is_admin():
        return "Running with administrator/root privileges. All features available."
    if platform.system().lower() == "windows":
        return "Not running as administrator. ARP discovery and some ICMP features may be limited."
    return "Not running as root. Some network features may be limited."