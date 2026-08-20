"""Turns a VmConfig into a qemu command line. Pure function, easy to test."""

import random

from .constants import (
    DISK_NAME,
    OVMF_CODE,
    OVMF_CODE_SECBOOT,
    QEMU,
)
from .errors import BladWirtualki


def random_mac():
    tail = (random.randint(0, 255) for _ in range(3))
    return "52:54:00:" + ":".join(f"{part:02x}" for part in tail)


def _firmware(machine, args):
    config = machine.config
    if config.firmware != "uefi":
        return
    code = OVMF_CODE_SECBOOT if config.secureboot else OVMF_CODE
    if not code.exists():
        raise BladWirtualki(f"brak firmware UEFI ({code}) - doinstaluj edk2-ovmf")
    args += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}"]
    args += ["-drive", f"if=pflash,format=raw,file={machine.nvram}"]


def _disk(args, path, index, bus, discard):
    options = [f"file={path}", "if=none", f"id=hd{index}", "format=qcow2", "cache=writeback"]
    if discard:
        options.append("discard=unmap")
    args += ["-drive", ",".join(options)]
    if bus == "virtio":
        args += ["-device", f"virtio-blk-pci,drive=hd{index}"]
    elif bus == "nvme":
        args += ["-device", f"nvme,drive=hd{index},serial=wt{index}"]
    else:
        args += ["-device", f"ide-hd,drive=hd{index},bus=ide.{index}"]


def _video(args, config):
    args += ["-vga", "none"]
    if config.gpu == "none":
        return

    size = f"xres={config.resolution.split('x')[0]},yres={config.resolution.split('x')[1]}" \
        if config.resolution else ""
    if config.gpu == "virtio":
        device = "virtio-vga-gl" if config.accel3d else "virtio-vga"
        parts = [device, "max_outputs=1"]
        if size:
            parts.append(size)
        args += ["-device", ",".join(parts)]
    elif config.gpu == "qxl":
        args += ["-device", f"qxl-vga,vram_size_mb={config.vram},ram_size_mb={config.vram}"]
    elif config.gpu == "vmware":
        args += ["-device", "vmware-svga"]
    else:
        args += ["-device", f"VGA,vgamem_mb={config.vram}"]


def _display(args, config):
    if config.display == "none":
        args += ["-display", "none"]
    elif config.display == "spice":
        args += ["-display", "spice-app"]
    elif config.display == "curses":
        args += ["-display", "curses"]
    else:
        suffix = ",gl=on" if config.accel3d else ""
        args += ["-display", config.display + suffix]
    if config.vnc:
        args += ["-vnc", f":{config.vnc}"]


def _network(args, config):
    if config.net == "none":
        args += ["-nic", "none"]
        return
    netdev = ["user", "id=net0"]
    for host, guest in config.ports:
        netdev.append(f"hostfwd=tcp::{host}-:{guest}")
    args += ["-netdev", ",".join(netdev)]
    device = "virtio-net-pci,netdev=net0"
    if config.mac:
        device += f",mac={config.mac}"
    args += ["-device", device]


def _shares(args, config):
    for index, share in enumerate(config.shares):
        args += [
            "-virtfs",
            f"local,path={share['path']},mount_tag={share['tag']},"
            f"security_model=mapped-xattr,id=fs{index}"
            + (",readonly=on" if share.get("ro") else ""),
        ]


def _usb(args, config):
    args += ["-device", "qemu-xhci,id=xhci"]
    if config.display != "none":
        args += ["-device", "usb-tablet"]
    for device in config.usb:
        vendor, product = device.split(":")
        args += ["-device", f"usb-host,vendorid=0x{vendor},productid=0x{product}"]


def _tpm(args, machine):
    args += ["-chardev", f"socket,id=chrtpm,path={machine.path / 'swtpm.sock'}"]
    args += ["-tpmdev", "emulator,id=tpm0,chardev=chrtpm"]
    args += ["-device", "tpm-tis,tpmdev=tpm0"]


def build(machine, iso=None, boot=None):
    config = machine.config
    config.validate()
    args = [QEMU, "-name", f"{config.name},process=wirtualka-{config.name}"]

    accel = ",accel=kvm" if config.kvm else ""
    args += ["-machine", config.machine + accel]
    args += ["-cpu", config.cpu_model if config.kvm else "qemu64"]
    args += ["-smp", str(config.cpus)]
    args += ["-m", str(config.ram_mb)]
    if config.balloon:
        # free-page-reporting hands unused guest RAM straight back to the host
        args += ["-device", "virtio-balloon,free-page-reporting=on"]
    args += ["-device", "virtio-rng-pci"]
    args += ["-rtc", "base=localtime"]

    _firmware(machine, args)

    disk_path = machine.path / DISK_NAME
    if disk_path.exists():
        _disk(args, disk_path, 0, config.bus, config.discard)
    for index, extra in enumerate(config.extra_disks, start=1):
        _disk(args, machine.path / extra, index, config.bus, config.discard)

    if iso:
        args += ["-drive", f"file={iso},media=cdrom,readonly=on"]

    order = boot or config.boot
    if order == "cd" or (order == "auto" and iso):
        args += ["-boot", "order=dc,menu=on"]
    elif order == "disk":
        args += ["-boot", "order=c"]
    elif order == "menu":
        args += ["-boot", "menu=on,splash-time=3000"]

    _video(args, config)
    _display(args, config)
    _network(args, config)
    _shares(args, config)
    _usb(args, config)

    if config.audio:
        args += ["-audio", "driver=pipewire,model=hda"]
    if config.clipboard and config.display in ("gtk", "spice"):
        args += ["-device", "virtio-serial-pci"]
        args += ["-chardev", "qemu-vdagent,id=vdagent,name=vdagent,clipboard=on"]
        args += ["-device", "virtserialport,chardev=vdagent,name=com.redhat.spice.0"]
    if config.tpm:
        _tpm(args, machine)

    args += ["-monitor", f"unix:{machine.monitor},server,nowait"]
    return args
