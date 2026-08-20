"""Starting and stopping machines. No daemon: a stopped machine is just a folder."""

import os
import re
import shutil
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


def prefix(config):
    parts = []
    if config.nice:
        parts += [need_binary("nice"), "-n", str(config.nice)]
    if config.pin:
        parts += [need_binary("taskset"), "-c", config.pin]
    return parts


def start(machine, iso=None, boot=None, foreground=False, console=False, fullscreen=False):
    if is_running(machine):
        raise Running(f"'{machine.name}' juz chodzi (pid {pid_of(machine)})")
    need_binary(QEMU)
    if machine.config.kvm and not os.access("/dev/kvm", os.R_OK | os.W_OK):
        raise BladWirtualki("brak dostepu do /dev/kvm - sprobuj z --no-kvm")
    if machine.config.tpm:
        _start_swtpm(machine)

    command = prefix(machine.config) + qemu.build(
        machine, iso=iso, boot=boot, console=console, fullscreen=fullscreen)
    machine.monitor.unlink(missing_ok=True)

    if foreground or console:
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


def pause(machine):
    return monitor(machine, "stop")


def resume(machine):
    return monitor(machine, "cont")


def reset(machine):
    return monitor(machine, "system_reset")


def change_cd(machine, path):
    return monitor(machine, f'change ide1-cd0 "{path}"')


def eject_cd(machine):
    return monitor(machine, "eject -f ide1-cd0")


def save_state(machine, name):
    answer = monitor(machine, f"savevm {name}")
    if "Error" in answer:
        raise BladWirtualki(answer.strip())
    return answer


def load_state(machine, name):
    answer = monitor(machine, f"loadvm {name}")
    if "Error" in answer:
        raise BladWirtualki(answer.strip())
    return answer


def screenshot(machine, path):
    """qemu zapisuje tylko PPM, wiec potem probujemy przerobic to na PNG."""
    raw = path.with_suffix(".ppm")
    monitor(machine, f'screendump "{raw}"')
    for _ in range(20):
        if raw.exists() and raw.stat().st_size:
            break
        time.sleep(0.25)
    if not raw.exists():
        raise BladWirtualki("nie udalo sie zrobic zrzutu")
    if path.suffix == ".png" and shutil.which("magick"):
        subprocess.run([shutil.which("magick"), str(raw), str(path)], check=False)
        if path.exists():
            raw.unlink(missing_ok=True)
            return path
    return raw


def wait_until_off(machine, timeout=None):
    waited = 0
    while is_running(machine):
        time.sleep(1)
        waited += 1
        if timeout and waited > timeout:
            return False
    return True


def running_machines(machines):
    return [machine for machine in machines if is_running(machine)]
