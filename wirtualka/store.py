"""Where machines live on disk: ~/wirtualka/machines/<name>/."""

import os
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import config as config_module
from . import disk
from .constants import (
    CONFIG_NAME,
    DISK_NAME,
    LOG_NAME,
    MACHINES_DIR,
    MONITOR_NAME,
    NVRAM_NAME,
    PID_NAME,
    ROOT,
)
from .errors import AlreadyExists, NotFound, BladWirtualki
from .util import check_name


@dataclass
class Machine:
    name: str
    path: Path
    config: "config_module.VmConfig"

    @property
    def disk(self):
        return self.path / DISK_NAME

    @property
    def config_file(self):
        return self.path / CONFIG_NAME

    @property
    def pid_file(self):
        return self.path / PID_NAME

    @property
    def log_file(self):
        return self.path / LOG_NAME

    @property
    def monitor(self):
        # unix sockets die past 108 bytes, so they live in the runtime dir
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
        sockets = runtime / "wirtualka"
        sockets.mkdir(parents=True, exist_ok=True)
        return sockets / f"{self.name}.sock"

    @property
    def nvram(self):
        return self.path / NVRAM_NAME

    def save(self):
        config_module.save(self.config, self.config_file)


def ensure_root():
    MACHINES_DIR.mkdir(parents=True, exist_ok=True)
    return ROOT


def path_of(name):
    return MACHINES_DIR / check_name(name)


def exists(name):
    return (path_of(name) / CONFIG_NAME).is_file()


def names():
    if not MACHINES_DIR.is_dir():
        return []
    return sorted(
        item.name for item in MACHINES_DIR.iterdir()
        if item.is_dir() and (item / CONFIG_NAME).is_file()
    )


def load(name):
    directory = path_of(name)
    if not (directory / CONFIG_NAME).is_file():
        raise NotFound(f"nie ma maszyny '{name}' (zobacz: wirtualka --list)")
    return Machine(name, directory, config_module.load(directory / CONFIG_NAME))


def all_machines():
    return [load(name) for name in names()]


def create(name, distro=None):
    if exists(name):
        raise AlreadyExists(f"maszyna '{name}' juz jest")
    directory = path_of(name)
    directory.mkdir(parents=True, exist_ok=True)
    machine = Machine(name, directory, config_module.VmConfig.new(name, distro))
    machine.save()
    return machine


def _guard(directory):
    """Never let a stray path send rmtree somewhere outside the store."""
    resolved = directory.resolve()
    if resolved.parent != MACHINES_DIR.resolve():
        raise BladWirtualki(f"{resolved} nie lezy w {MACHINES_DIR}, nie ruszam")
    return resolved


def delete(name):
    machine = load(name)
    shutil.rmtree(_guard(machine.path))
    return machine.path


def rename(old, new):
    machine = load(old)
    check_name(new)
    if exists(new):
        raise AlreadyExists(f"maszyna '{new}' juz jest")
    target = path_of(new)
    _guard(machine.path).rename(target)
    machine.config.name = new
    Machine(new, target, machine.config).save()
    return target


def clone(source_name, new_name, linked=True):
    source = load(source_name)
    if exists(new_name):
        raise AlreadyExists(f"maszyna '{new_name}' juz jest")
    check_name(new_name)
    target = path_of(new_name)
    target.mkdir(parents=True)

    clone_config = config_module.VmConfig.from_dict(source.config.to_dict())
    clone_config.name = new_name
    clone_config.created = date.today().isoformat()
    clone_config.mac = ""
    machine = Machine(new_name, target, clone_config)

    if source.disk.exists():
        if linked:
            disk.link_clone(source.disk, machine.disk)
        else:
            shutil.copy2(source.disk, machine.disk)
    if source.nvram.exists():
        shutil.copy2(source.nvram, machine.nvram)
    machine.save()
    return machine
