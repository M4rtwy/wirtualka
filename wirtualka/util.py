import shutil

from .constants import MIN_RAM_MB, NAME_RE, PORT_RE, SIZE_RE
from .errors import BladWirtualki

UNITS = {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024**2}


def parse_size_mb(text):
    """'4G' -> 4096. Bare numbers are megabytes."""
    match = SIZE_RE.match(str(text).strip())
    if not match:
        raise BladWirtualki(f"nie rozumiem rozmiaru: {text}")
    value, unit = float(match.group(1)), (match.group(2) or "M").upper()
    return int(value * UNITS[unit])


def format_size_mb(mb):
    if mb >= 1024 and mb % 1024 == 0:
        return f"{mb // 1024}G"
    return f"{mb}M"


def check_name(name):
    if not NAME_RE.match(str(name)):
        raise BladWirtualki(f"zla nazwa '{name}' - male litery, cyfry, - i _, max 32 znaki")
    return name


def check_ram(mb):
    if mb < MIN_RAM_MB:
        raise BladWirtualki(f"za malo ramu: {mb}M (minimum {MIN_RAM_MB}M)")
    return mb


def parse_port(text):
    match = PORT_RE.match(str(text).strip())
    if not match:
        raise BladWirtualki(f"port ma wygladac tak HOST:GOSC, a nie '{text}'")
    host, guest = int(match.group(1)), int(match.group(2))
    for port in (host, guest):
        if not 1 <= port <= 65535:
            raise BladWirtualki(f"port poza zakresem: {port}")
    return host, guest


def need_binary(name):
    path = shutil.which(name)
    if not path:
        raise BladWirtualki(f"brakuje programu '{name}'")
    return path


def human_bytes(size):
    step = float(size)
    for unit in ("B", "K", "M", "G", "T"):
        if step < 1024 or unit == "T":
            return f"{step:.0f}{unit}" if unit == "B" else f"{step:.1f}{unit}"
        step /= 1024
