"""Optional dependency detection."""
import shutil
import platform
import sys
import subprocess
from ..utils.logger import get_logger

log = get_logger(__name__)


def check_dependency(name: str, command: list) -> bool:
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False)
        return True
    except Exception:
        return False


def get_optional_dependencies() -> dict:
    return {
        "nmap": check_dependency("nmap", ["nmap", "--version"]),
        "scapy": check_dependency("scapy", [sys.executable, "-c", "import scapy"]),
        "pysnmp": check_dependency("pysnmp", [sys.executable, "-c", "import pysnmp"]),
        "putty": shutil.which("putty") is not None,
        "winscp": shutil.which("winscp") is not None,
        "powershell": shutil.which("powershell") is not None or shutil.which("pwsh") is not None,
    }