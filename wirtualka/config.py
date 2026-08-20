"""One machine as stored in vm.json."""

import json
from dataclasses import asdict, dataclass, field, fields
from datetime import date

from .constants import DEFAULTS, DISK_BUSES, DISPLAYS, FIRMWARES, GPUS, MAX_PORTS, MAX_SHARES, NETS
from .errors import BladWirtualki
from .util import check_name, check_ram, format_size_mb, parse_size_mb


@dataclass
class VmConfig:
    name: str
    created: str = ""
    distro: str = ""
    iso: str = ""
    ram_mb: int = 4096
    cpus: int = DEFAULTS["cpus"]
    cpu_model: str = DEFAULTS["cpu_model"]
    machine: str = DEFAULTS["machine"]
    disk_mb: int = 40960
    bus: str = DEFAULTS["bus"]
    extra_disks: list = field(default_factory=list)
    display: str = DEFAULTS["display"]
    gpu: str = DEFAULTS["gpu"]
    vram: int = DEFAULTS["vram"]
    accel3d: bool = DEFAULTS["accel3d"]
    resolution: str = ""
    net: str = DEFAULTS["net"]
    ports: list = field(default_factory=list)
    ports_udp: list = field(default_factory=list)
    dns: str = ""
    hostname: str = ""
    mac: str = ""
    audio: bool = DEFAULTS["audio"]
    clipboard: bool = DEFAULTS["clipboard"]
    firmware: str = DEFAULTS["firmware"]
    secureboot: bool = DEFAULTS["secureboot"]
    tpm: bool = DEFAULTS["tpm"]
    kvm: bool = DEFAULTS["kvm"]
    balloon: bool = DEFAULTS["balloon"]
    discard: bool = DEFAULTS["discard"]
    shares: list = field(default_factory=list)
    usb: list = field(default_factory=list)
    boot: str = "auto"
    temporary: bool = False
    fast_disk: bool = False
    nested: bool = False
    pin: str = ""
    nice: int = 0
    keyboard: str = ""
    rtc: str = "localtime"
    sound_model: str = "hda"
    fit: bool = True
    screens: int = 1
    vnc: int = 0
    note: str = ""

    def validate(self):
        check_name(self.name)
        check_ram(self.ram_mb)
        if not 1 <= self.cpus <= 64:
            raise BladWirtualki(f"dziwna liczba rdzeni: {self.cpus}")
        for value, allowed, label in (
            (self.display, DISPLAYS, "--display"),
            (self.gpu, GPUS, "--gpu"),
            (self.net, NETS, "--net"),
            (self.firmware, FIRMWARES, "--uefi/--bios"),
            (self.bus, DISK_BUSES, "--bus"),
        ):
            if value not in allowed:
                raise BladWirtualki(f"{label}: '{value}' - moze byc: {', '.join(allowed)}")
        if self.rtc not in ("localtime", "utc"):
            raise BladWirtualki(f"--rtc: '{self.rtc}' - moze byc localtime albo utc")
        if self.sound_model not in ("hda", "ac97", "es1370"):
            raise BladWirtualki(f"--sound-model: '{self.sound_model}'")
        if not 1 <= self.screens <= 4:
            raise BladWirtualki("liczba ekranow: od 1 do 4")
        if not -20 <= self.nice <= 19:
            raise BladWirtualki("--nice: od -20 do 19")
        if len(self.ports) + len(self.ports_udp) > MAX_PORTS:
            raise BladWirtualki(f"za duzo przekierowanych portow (max {MAX_PORTS})")
        if len(self.shares) > MAX_SHARES:
            raise BladWirtualki(f"za duzo folderow (max {MAX_SHARES})")
        if self.secureboot and self.firmware != "uefi":
            raise BladWirtualki("secure boot dziala tylko z UEFI")
        if self.resolution and "x" not in self.resolution:
            raise BladWirtualki(f"rozdzielczosc ma wygladac tak 1920x1080, a nie '{self.resolution}'")
        return self

    def summary(self):
        return {
            "nazwa": self.name,
            "system": self.distro or "-",
            "ram": format_size_mb(self.ram_mb),
            "rdzenie": self.cpus,
            "dysk": format_size_mb(self.disk_mb),
            "ekran": self.display,
            "gpu": self.gpu + (" +3d" if self.accel3d else ""),
            "siec": "brak" if self.net == "none" else self.net,
            "firmware": self.firmware + (" +secureboot" if self.secureboot else ""),
        }

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, raw):
        known = {item.name for item in fields(cls)}
        unknown = set(raw) - known
        if unknown:
            raise BladWirtualki(f"nieznane pola w vm.json: {', '.join(sorted(unknown))}")
        if "name" not in raw:
            raise BladWirtualki("vm.json bez pola 'name'")
        return cls(**raw).validate()

    @classmethod
    def new(cls, name, distro=None):
        config = cls(name=name, created=date.today().isoformat())
        if distro:
            config.distro = distro.slug
            config.ram_mb = parse_size_mb(distro.ram)
            config.disk_mb = parse_size_mb(distro.disk)
        return config


def load(path):
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise BladWirtualki(f"popsute {path}: {error}") from None
    return VmConfig.from_dict(raw)


def save(config, path):
    config.validate()
    path.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n")
