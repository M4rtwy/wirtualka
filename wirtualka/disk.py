"""qcow2 disks. Sparse, so a 60G image costs almost nothing until written to."""

import json
import subprocess

from .constants import QEMU_IMG
from .errors import BladWirtualki
from .util import need_binary


def _run(*args, capture=True):
    need_binary(QEMU_IMG)
    result = subprocess.run([QEMU_IMG, *args], capture_output=capture, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip() if capture else ""
        raise BladWirtualki(f"qemu-img {args[0]} nie dal rady: {message}")
    return result.stdout if capture else ""


def create(path, size_mb):
    if path.exists():
        raise BladWirtualki(f"dysk juz istnieje: {path}")
    _run("create", "-f", "qcow2", "-o", "lazy_refcounts=on", str(path), f"{size_mb}M")
    return path


def info(path):
    if not path.exists():
        raise BladWirtualki(f"nie ma dysku {path}")
    return json.loads(_run("info", "--output=json", str(path)))


def used_bytes(path):
    try:
        return int(info(path).get("actual-size") or path.stat().st_size)
    except BladWirtualki:
        return 0


def resize(path, size_mb):
    current = info(path)["virtual-size"] // (1024 * 1024)
    if size_mb < current:
        raise BladWirtualki(f"zmniejszanie dysku kasuje dane - teraz jest {current}M")
    _run("resize", str(path), f"{size_mb}M")


def snapshots(path):
    data = info(path).get("snapshots") or []
    return [(item["name"], item.get("date-sec", 0), item.get("vm-state-size", 0)) for item in data]


def snapshot_create(path, name):
    if any(existing == name for existing, _, _ in snapshots(path)):
        raise BladWirtualki(f"snapshot '{name}' juz jest")
    _run("snapshot", "-c", name, str(path))


def snapshot_restore(path, name):
    _run("snapshot", "-a", name, str(path))


def snapshot_delete(path, name):
    _run("snapshot", "-d", name, str(path))


def link_clone(source, dest):
    fmt = info(source).get("format", "qcow2")
    _run("create", "-f", "qcow2", "-b", str(source), "-F", fmt, str(dest))
