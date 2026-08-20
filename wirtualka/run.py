"""Starting and stopping machines. There is no daemon: a stopped machine
is just a folder with a qcow2 file in it."""

import os
import re
import signal
import socket
import subprocess
import time

from . import qemu
from .constants import QEMU
from .errors import Running, BladWirtualki
from .util import need_binary

STOP_TIMEOUT = 30


def pid_of(machine):
    try:
        pid = int(machine.pid_file.read_text().strip())
    except (OSError, ValueError):
        return None
    try:
        cmdline = open(f"/proc/{pid}/cmdline", "rb").read().decode("utf-8", "replace")
    except OSError:
        machine.pid_file.unlink(missing_ok=True)
        return None
    if f"wirtualka-{machine.name}" not in cmdline:
        machine.pid_file.unlink(missing_ok=True)
        return None
    return pid


def is_running(machine):
    return pid_of(machine) is not None


def uptime(machine):
    pid = pid_of(machine)
    if not pid:
        return 0
    return int(time.time() - os.stat(f"/proc/{pid}").st_mtime)


def rss_mb(machine):
    pid = pid_of(machine)
    if not pid:
        return 0
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def monitor(machine, command):
    """Talk to qemu's own monitor socket - that is how we power off politely."""
    if not machine.monitor.exists():
        raise BladWirtualki("brak gniazda monitora - maszyna chyba nie chodzi")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(machine.monitor))
        time.sleep(0.2)
        client.sendall(command.encode() + b"\n")
        time.sleep(0.3)
        try:
            raw = client.recv(65536).decode("utf-8", "replace")
        except socket.timeout:
            return ""
    return _clean(raw, command)


ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07")


def _clean(text, command):
    """The monitor echoes what we typed, one keypress at a time."""
    lines = []
    for line in ANSI.sub("", text).splitlines():
        line = line.replace("(qemu)", "").strip()
        if line and command not in line and not line.startswith("QEMU "):
            lines.append(line)
    return "\n".join(lines)


def _start_swtpm(machine):
    need_binary("swtpm")
    state = machine.path / "tpm"
    state.mkdir(exist_ok=True)
    subprocess.Popen(
        ["swtpm", "socket", "--tpmstate", f"dir={state}",
         "--ctrl", f"type=unixio,path={machine.path / 'swtpm.sock'}",
         "--tpm2", "--terminate"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    for _ in range(50):
        if (machine.path / "swtpm.sock").exists():
            return
        time.sleep(0.1)
    raise BladWirtualki("swtpm sie nie odpalil")


def start(machine, iso=None, boot=None, foreground=False):
    if is_running(machine):
        raise Running(f"'{machine.name}' juz chodzi (pid {pid_of(machine)})")
    need_binary(QEMU)
    if machine.config.kvm and not os.access("/dev/kvm", os.R_OK | os.W_OK):
        raise BladWirtualki("brak dostepu do /dev/kvm - sprobuj z --no-kvm")
    if machine.config.tpm:
        _start_swtpm(machine)

    command = qemu.build(machine, iso=iso, boot=boot)
    machine.monitor.unlink(missing_ok=True)

    if foreground:
        return subprocess.call(command)

    with open(machine.log_file, "ab") as log:
        log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n".encode())
        process = subprocess.Popen(
            command, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    machine.pid_file.write_text(str(process.pid))

    time.sleep(1.0)
    if process.poll() is not None:
        machine.pid_file.unlink(missing_ok=True)
        tail = machine.log_file.read_text()[-1500:]
        raise BladWirtualki(f"qemu padl od razu:\n{tail}")
    return process.pid


def stop(machine, force=False, timeout=STOP_TIMEOUT):
    pid = pid_of(machine)
    if not pid:
        return False
    if force:
        os.kill(pid, signal.SIGKILL)
    else:
        try:
            monitor(machine, "system_powerdown")
        except BladWirtualki:
            os.kill(pid, signal.SIGTERM)
        for _ in range(timeout * 2):
            if not is_running(machine):
                break
            time.sleep(0.5)
        if is_running(machine):
            os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if not is_running(machine):
            break
        time.sleep(0.25)
    machine.pid_file.unlink(missing_ok=True)
    machine.monitor.unlink(missing_ok=True)
    return True
