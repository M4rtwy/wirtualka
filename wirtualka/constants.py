"""Paths, defaults and limits. Nothing here touches the disk."""

import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("WIRTUALKA_HOME", Path.home() / "wirtualka"))
MACHINES_DIR = ROOT / "machines"
ISO_DIR = ROOT / "iso"
TEMPLATE_FILE = ROOT / "templates.json"

CONFIG_NAME = "vm.json"
DISK_NAME = "disk.qcow2"
PID_NAME = "vm.pid"
LOG_NAME = "vm.log"
MONITOR_NAME = "monitor.sock"
NVRAM_NAME = "OVMF_VARS.fd"

QEMU = "qemu-system-x86_64"
QEMU_IMG = "qemu-img"
OVMF_CODE = Path("/usr/share/edk2/x64/OVMF_CODE.4m.fd")
OVMF_CODE_SECBOOT = Path("/usr/share/edk2/x64/OVMF_CODE.secboot.4m.fd")
OVMF_VARS = Path("/usr/share/edk2/x64/OVMF_VARS.4m.fd")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([KMGT])?B?$", re.I)
PORT_RE = re.compile(r"^(\d{1,5}):(\d{1,5})$")

DISPLAYS = ("gtk", "sdl", "spice", "none", "curses")
GPUS = ("virtio", "qxl", "vmware", "std", "none")
NETS = ("user", "none")
FIRMWARES = ("uefi", "bios")
DISK_BUSES = ("virtio", "sata", "nvme")

DEFAULTS = {
    "ram": "4G",
    "cpus": 4,
    "disk": "40G",
    "display": "gtk",
    "gpu": "virtio",
    "net": "user",
    "firmware": "uefi",
    "bus": "virtio",
    "audio": True,
    "accel3d": False,
    "kvm": True,
    "balloon": True,
    "discard": True,
    "clipboard": True,
    "tpm": False,
    "secureboot": False,
    "cpu_model": "host",
    "machine": "q35",
    "vram": 64,
}

# Guest RAM is given back to the host through the balloon device, so an idle
# VM does not sit on the full --ram figure.
MIN_RAM_MB = 256
MAX_PORTS = 16
MAX_SHARES = 4
