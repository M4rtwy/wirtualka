"""What every flag actually does."""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from . import catalog, disk, iso, qemu, run, store, templates
from .config import VmConfig
from .constants import ISO_DIR, MACHINES_DIR, QEMU, ROOT
from .errors import BladWirtualki
from .util import format_size_mb, human_bytes, parse_port, parse_size_mb

LAST_FILE = ROOT / "last"


def say(args, *text):
    if not args.quiet:
        print(*text)


def remember(name):
    ROOT.mkdir(parents=True, exist_ok=True)
    LAST_FILE.write_text(name)


def pick_name(args):
    if args.name:
        return args.name
    known = store.names()
    if len(known) == 1:
        return known[0]
    if LAST_FILE.is_file():
        last = LAST_FILE.read_text().strip()
        if last in known:
            return last
    if not known:
        raise BladWirtualki("nie masz zadnej maszyny - zacznij od: wirtualka --new -d cachyos")
    raise BladWirtualki("podaj nazwe maszyny, masz kilka: " + ", ".join(known))


def confirm(args, question):
    if args.yes:
        return True
    return input(f"{question} [t/N] ").strip().lower() in ("t", "tak", "y", "yes")


def tag_for(path):
    return re.sub(r"[^a-z0-9]+", "", path.name.lower())[:16] or "share"


def apply_flags(config, args):
    simple = ("cpus", "cpu_model", "machine", "bus", "display", "gpu", "vram",
              "resolution", "mac", "net", "firmware", "pin", "keyboard", "rtc",
              "sound_model", "dns", "hostname", "note")
    for key in simple:
        value = getattr(args, key, None)
        if value is not None:
            setattr(config, key, value)
    for key in ("audio", "clipboard", "kvm", "balloon", "discard", "accel3d",
                "secureboot", "tpm", "temporary", "fast_disk", "nested", "fit"):
        value = getattr(args, key, None)
        if value is not None:
            setattr(config, key, value)

    if args.ram:
        config.ram_mb = parse_size_mb(args.ram)
    if args.vnc is not None:
        config.vnc = args.vnc
    if args.nice is not None:
        config.nice = args.nice
    if args.screens is not None:
        config.screens = args.screens
    for item in args.port_udp:
        pair = list(parse_port(item))
        if pair not in config.ports_udp:
            config.ports_udp.append(pair)
    if args.no_internet:
        config.net = "none"
    if args.headless:
        config.display = "none"
    if args.no_ports:
        config.ports = []
    if args.ssh:
        args.port.append("2222:22")
    for item in args.port:
        pair = list(parse_port(item))
        if pair not in config.ports:
            config.ports.append(pair)
    for folder, readonly in [(f, False) for f in args.share] + [(f, True) for f in args.share_ro]:
        path = Path(folder).expanduser().resolve()
        if not path.is_dir():
            raise BladWirtualki(f"nie ma folderu {path}")
        entry = {"tag": tag_for(path), "path": str(path), "ro": readonly}
        config.shares = [s for s in config.shares if s["tag"] != entry["tag"]] + [entry]
    if args.unshare:
        config.shares = [s for s in config.shares if s["tag"] != args.unshare]
    for device in args.usb:
        if not re.match(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$", device):
            raise BladWirtualki(f"--usb chce VID:PID po hex, np. 046d:c52b, a nie '{device}'")
        if device not in config.usb:
            config.usb.append(device)
    return config.validate()



def cmd_list(args):
    machines = store.all_machines()
    if args.json:
        print(json.dumps([m.config.to_dict() for m in machines], indent=2, ensure_ascii=False))
        return 0
    if not machines:
        print("pusto. zacznij od: wirtualka --new -d cachyos")
        return 0
    print(f"{'nazwa':16} {'system':16} {'ram':>6} {'cpu':>4} {'dysk':>6} {'zajete':>8}  stan")
    for machine in machines:
        state = f"chodzi (pid {run.pid_of(machine)})" if run.is_running(machine) else "stoi"
        used = human_bytes(disk.used_bytes(machine.disk)) if machine.disk.exists() else "-"
        config = machine.config
        print(f"{config.name:16} {(config.distro or '-'):16} "
              f"{format_size_mb(config.ram_mb):>6} {config.cpus:>4} "
              f"{format_size_mb(config.disk_mb):>6} {used:>8}  {state}")
    return 0


def cmd_iso_list(args):
    print(f"{'id':18} {'system':26} ram    dysk")
    for distro in catalog.CATALOG:
        mark = "  (wlasne ISO)" if distro.manual else ""
        print(f"{distro.slug:18} {distro.name:26} {distro.ram:<6} {distro.disk}{mark}")
    print("\nuzycie: wirtualka --new -d cachyos")
    return 0


def cmd_iso_cache(args):
    files = iso.cached()
    if not files:
        print("cache pusty")
        return 0
    for path in files:
        print(f"{human_bytes(path.stat().st_size):>8}  {path.name}")
    total = sum(path.stat().st_size for path in files)
    print(f"{human_bytes(total):>8}  razem")
    return 0


def cmd_usage(args):
    rows = []
    for machine in store.all_machines():
        size = sum(f.stat().st_size for f in machine.path.rglob("*") if f.is_file())
        rows.append((machine.name, size))
    isos = sum(path.stat().st_size for path in iso.cached())
    for name, size in sorted(rows, key=lambda row: -row[1]):
        print(f"{human_bytes(size):>8}  {name}")
    print(f"{human_bytes(isos):>8}  ISO")
    print(f"{human_bytes(sum(size for _, size in rows) + isos):>8}  razem")
    return 0


def cmd_where(args):
    print(f"maszyny: {MACHINES_DIR}")
    print(f"ISO:     {ISO_DIR}")
    print(f"program: {Path(__file__).resolve().parent}")
    return 0


def cmd_info(args, machine):
    if args.json:
        print(json.dumps(machine.config.to_dict(), indent=2, ensure_ascii=False))
        return 0
    for key, value in machine.config.summary().items():
        print(f"  {key:10} {value}")
    config = machine.config
    if config.ports:
        print("  porty      " + ", ".join(f"{h}->{g}" for h, g in config.ports))
    for share in config.shares:
        print(f"  folder     {share['path']} (tag {share['tag']}"
              + (", tylko odczyt)" if share["ro"] else ")"))
    if config.usb:
        print("  usb        " + ", ".join(config.usb))
    if config.iso:
        print(f"  plyta      {config.iso}")
    print(f"  folder     {machine.path}")
    return 0


def cmd_status(args, machine):
    if run.is_running(machine):
        minutes = run.uptime(machine) // 60
        print(f"{machine.name}: chodzi, pid {run.pid_of(machine)}, "
              f"{run.rss_mb(machine)}M ramu, {minutes} min")
    else:
        print(f"{machine.name}: stoi (nie bierze ani ramu, ani procesora)")
    return 0



def resolve_iso(args, config, quiet):
    if args.iso:
        return iso.find_cached(args.iso)
    if args.distro:
        return iso.ensure(args.distro, quiet=quiet)
    if config.iso:
        return Path(config.iso)
    return None


def cmd_new(args):
    name = args.new if isinstance(args.new, str) else args.name
    distro = None
    if not args.iso:
        distro = catalog.get(args.distro or "cachyos")
    name = name or (distro.slug if distro else "vm")
    if store.exists(name):
        suffix = 2
        while store.exists(f"{name}{suffix}"):
            suffix += 1
        name = f"{name}{suffix}"

    store.ensure_root()
    machine = store.create(name, distro)
    if args.template:
        templates.apply(args.template, machine.config)
    if args.disk:
        machine.config.disk_mb = parse_size_mb(args.disk)

    media = resolve_iso(args, machine.config, args.quiet)
    if media:
        machine.config.iso = str(media)
        machine.config.boot = "cd"
    apply_flags(machine.config, args)
    machine.save()

    disk.create(machine.disk, machine.config.disk_mb)
    if machine.config.firmware == "uefi":
        _prepare_nvram(machine)
    remember(name)

    say(args, f"zrobione: {name} ({format_size_mb(machine.config.ram_mb)} ramu, "
              f"{machine.config.cpus} rdzenie, dysk {format_size_mb(machine.config.disk_mb)})")
    if args.no_start or args.dry_run:
        if args.dry_run:
            print(shlex.join(qemu.build(machine, iso=media)))
        return 0
    return cmd_start(args, machine, media)


def _prepare_nvram(machine):
    from .constants import OVMF_VARS
    if not machine.nvram.exists():
        if not OVMF_VARS.exists():
            raise BladWirtualki(f"brak {OVMF_VARS} - doinstaluj edk2-ovmf")
        machine.nvram.write_bytes(OVMF_VARS.read_bytes())


def cmd_doctor(args):
    import shutil as _shutil
    from .constants import OVMF_CODE

    checks = []
    virt = any(flag in open("/proc/cpuinfo").read() for flag in ("vmx", "svm"))
    checks.append((virt, "procesor umie wirtualizacje",
                   "wlacz VT-x/AMD-V w BIOSie"))
    checks.append((os.access("/dev/kvm", os.R_OK | os.W_OK), "mam dostep do /dev/kvm",
                   "dopisz sie do grupy kvm albo uzywaj --no-kvm"))
    checks.append((bool(_shutil.which(QEMU)), "qemu jest zainstalowane",
                   "doinstaluj qemu-desktop"))
    checks.append((OVMF_CODE.exists(), "firmware UEFI jest",
                   "doinstaluj edk2-ovmf albo uzywaj --bios"))
    checks.append((bool(_shutil.which("swtpm")), "swtpm jest (potrzebny do Windowsa 11)",
                   "doinstaluj swtpm, jesli chcesz Windowsa 11"))
    free = os.statvfs(str(ROOT.parent))
    gigabytes = free.f_bavail * free.f_frsize / (1024 ** 3)
    checks.append((gigabytes > 20, f"wolnego miejsca: {gigabytes:.0f} GB",
                   "zrob miejsce, maszyny lubia dysk"))

    for good, label, hint in checks:
        print(f"  {'[ok] ' if good else '[!!] '}{label}")
        if not good:
            print(f"        -> {hint}")
    return 0 if all(good for good, _, _ in checks) else 1


def cmd_all_stop(args):
    stopped = 0
    for machine in store.all_machines():
        if run.is_running(machine):
            run.stop(machine)
            say(args, f"{machine.name} zatrzymana")
            stopped += 1
    if not stopped:
        say(args, "nic nie chodzilo")
    return 0


def cmd_running(args):
    machines = run.running_machines(store.all_machines())
    if not machines:
        print("nic nie chodzi")
        return 0
    for machine in machines:
        print(f"{machine.name:16} pid {run.pid_of(machine):<8} "
              f"{run.rss_mb(machine)}M ramu, {run.uptime(machine) // 60} min")
    return 0


def cmd_export(args, machine):
    import tarfile

    if run.is_running(machine):
        raise BladWirtualki("najpierw zatrzymaj maszyne")
    target = Path(args.export).expanduser()
    with tarfile.open(target, "w:gz") as archive:
        archive.add(machine.path, arcname=machine.name)
    say(args, f"spakowane: {target} ({human_bytes(target.stat().st_size)})")
    return 0


def cmd_import(args):
    import tarfile

    source = Path(args.import_file).expanduser()
    if not source.is_file():
        raise BladWirtualki(f"nie ma pliku {source}")
    store.ensure_root()
    with tarfile.open(source) as archive:
        names = {Path(item.name).parts[0] for item in archive.getmembers() if item.name}
        if len(names) != 1:
            raise BladWirtualki("to nie wyglada na spakowana maszyne")
        name = names.pop()
        if store.exists(name):
            raise BladWirtualki(f"maszyna '{name}' juz jest")
        archive.extractall(MACHINES_DIR, filter="data")
    machine = store.load(name)
    machine.config.name = name
    machine.save()
    say(args, f"wypakowane: {name}")
    return 0


def cmd_ssh(args, machine):
    port = next((host for host, guest in machine.config.ports if guest == 22), None)
    if not port:
        raise BladWirtualki(f"brak przekierowania na ssh - zrob: "
                            f"wirtualka {machine.name} --ssh")
    user = os.environ.get("USER", "root")
    return subprocess.call(["ssh", "-p", str(port), f"{user}@127.0.0.1"])


def cmd_screenshot(args, machine):
    if not run.is_running(machine):
        raise BladWirtualki("maszyna stoi, nie ma czego fotografowac")
    if isinstance(args.screenshot, str):
        target = Path(args.screenshot).expanduser()
    else:
        folder = Path.home() / "Obrazy"
        folder = folder if folder.is_dir() else Path.cwd()
        target = folder / f"{machine.name}-{int(time.time())}.png"
    saved = run.screenshot(machine, target)
    say(args, f"zrzut: {saved}")
    return 0


def cmd_start(args, machine, media=None):
    media = media if media is not None else resolve_iso(args, machine.config, args.quiet)
    if args.no_iso:
        media = None
    if machine.config.firmware == "uefi":
        _prepare_nvram(machine)
    if args.dry_run:
        print(shlex.join(run.prefix(machine.config)
                         + qemu.build(machine, iso=media, console=args.console,
                                      fullscreen=args.fullscreen)))
        return 0

    pid = run.start(machine, iso=media, foreground=args.fg, console=args.console,
                    fullscreen=args.fullscreen)
    if args.console:
        return pid
    remember(machine.name)
    if not args.fg:
        say(args, f"{machine.name} chodzi (pid {pid})")
        if media:
            say(args, f"po instalacji odpalaj tak: wirtualka {machine.name} --no-iso")
    if args.wait:
        run.wait_until_off(machine)
        say(args, f"{machine.name} sie wylaczyla")
    return 0


def cmd_stop(args, machine, force=False):
    if not run.is_running(machine):
        say(args, f"{machine.name} i tak stoi")
        return 0
    run.stop(machine, force=force)
    say(args, f"{machine.name} zatrzymana")
    return 0


def cmd_rm(args, machine):
    if run.is_running(machine):
        raise BladWirtualki(f"'{machine.name}' chodzi - najpierw: wirtualka {machine.name} --stop")
    size = human_bytes(disk.used_bytes(machine.disk)) if machine.disk.exists() else "0B"
    if not confirm(args, f"skasowac '{machine.name}' razem z dyskiem ({size})?"):
        print("nic nie robie")
        return 1
    store.delete(machine.name)
    say(args, f"skasowane: {machine.name}")
    return 0


def cmd_edit(args, machine):
    editor = os.environ.get("EDITOR") or "nano"
    subprocess.call([editor, str(machine.config_file)])
    store.load(machine.name)
    return 0


def cmd_snapshots(args, machine):
    rows = disk.snapshots(machine.disk)
    if not rows:
        print("brak snapshotow")
        return 0
    for name, when, _ in rows:
        import datetime
        stamp = datetime.datetime.fromtimestamp(when).strftime("%Y-%m-%d %H:%M") if when else "-"
        print(f"  {name:24} {stamp}")
    return 0



GLOBAL = {
    "doctor": cmd_doctor,
    "all_stop": cmd_all_stop,
    "running": cmd_running,
    "list": cmd_list,
    "iso_list": cmd_iso_list,
    "iso_cache": cmd_iso_cache,
    "usage": cmd_usage,
    "where": cmd_where,
}


def dispatch(args, parser):
    if args.gui:
        from .gui import main as gui_main
        return gui_main()

    for flag, handler in GLOBAL.items():
        if getattr(args, flag):
            return handler(args)

    if args.iso_get:
        path = iso.ensure(args.iso_get, quiet=args.quiet)
        say(args, f"mam: {path}")
        return 0
    if args.iso_rm:
        say(args, f"skasowane: {iso.remove(args.iso_rm).name}")
        return 0
    if args.template_list:
        data = templates.load_all()
        print("\n".join(sorted(data)) or "brak szablonow")
        return 0
    if args.template_rm:
        templates.delete(args.template_rm)
        return 0
    if args.import_file:
        return cmd_import(args)
    if args.new:
        return cmd_new(args)

    if not args.name and len(sys.argv) <= 1:
        parser.print_help()
        return 0

    machine = store.load(pick_name(args))
    config = machine.config

    if args.rename:
        store.rename(machine.name, args.rename)
        say(args, f"{machine.name} -> {args.rename}")
        return 0
    if args.clone:
        copy = store.clone(machine.name, args.clone, linked=not args.full_clone)
        say(args, f"kopia gotowa: {copy.name}")
        return 0
    if args.rm:
        return cmd_rm(args, machine)

    if args.template:
        templates.apply(args.template, config)
    changed = apply_flags(config, args)
    if args.no_iso and not args.once:
        config.iso = ""
        config.boot = "auto"
    if args.save_template:
        templates.save(args.save_template, config)
        say(args, f"szablon zapisany: {args.save_template}")
    if not args.once:
        machine.config = changed
        machine.save()

    if args.resize:
        disk.resize(machine.disk, parse_size_mb(args.resize))
        config.disk_mb = parse_size_mb(args.resize)
        machine.save()
        say(args, f"dysk ma teraz {args.resize}")
        return 0
    if args.disk_add:
        extra = f"disk{len(config.extra_disks) + 1}.qcow2"
        disk.create(machine.path / extra, parse_size_mb(args.disk_add))
        config.extra_disks.append(extra)
        machine.save()
        say(args, f"dolozony dysk {extra}")
        return 0
    if args.snap:
        disk.snapshot_create(machine.disk, args.snap)
        say(args, f"snapshot '{args.snap}' zapisany")
        return 0
    if args.snaps:
        return cmd_snapshots(args, machine)
    if args.snap_back:
        if run.is_running(machine):
            raise BladWirtualki("najpierw zatrzymaj maszyne")
        disk.snapshot_restore(machine.disk, args.snap_back)
        say(args, f"wrocone do '{args.snap_back}'")
        return 0
    if args.snap_rm:
        disk.snapshot_delete(machine.disk, args.snap_rm)
        return 0
    if args.export:
        return cmd_export(args, machine)
    if args.open:
        subprocess.Popen(["xdg-open", str(machine.path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    if args.ssh_into:
        return cmd_ssh(args, machine)
    if args.screenshot:
        return cmd_screenshot(args, machine)
    if args.pause:
        run.pause(machine)
        say(args, "zamrozone")
        return 0
    if args.resume:
        run.resume(machine)
        say(args, "odmrozone")
        return 0
    if args.reset:
        run.reset(machine)
        return 0
    if args.cd:
        run.change_cd(machine, iso.find_cached(args.cd))
        say(args, "plyta wlozona")
        return 0
    if args.eject:
        run.eject_cd(machine)
        say(args, "plyta wyjeta")
        return 0
    if args.save_state:
        run.save_state(machine, args.save_state)
        say(args, f"stan '{args.save_state}' zapisany razem z pamiecia")
        return 0
    if args.load_state:
        run.load_state(machine, args.load_state)
        say(args, f"wczytane: {args.load_state}")
        return 0
    if args.disk_rm:
        index = args.disk_rm - 1
        if not 0 <= index < len(config.extra_disks):
            raise BladWirtualki(f"nie ma dolozonego dysku numer {args.disk_rm}")
        removed = config.extra_disks.pop(index)
        (machine.path / removed).unlink(missing_ok=True)
        machine.save()
        say(args, f"usuniety {removed}")
        return 0
    if args.wait and not args.start:
        run.wait_until_off(machine)
        return 0
    if args.monitor:
        print(run.monitor(machine, args.monitor).strip())
        return 0
    if args.log:
        if machine.log_file.exists():
            print(machine.log_file.read_text()[-4000:])
        return 0
    if args.kill:
        return cmd_stop(args, machine, force=True)
    if args.stop:
        return cmd_stop(args, machine)
    if args.restart:
        cmd_stop(args, machine)
        return cmd_start(args, machine)
    if args.status:
        return cmd_status(args, machine)
    if args.info:
        return cmd_info(args, machine)
    if (args.start or args.dry_run or args.no_internet or args.no_iso
            or args.console or args.fullscreen):
        return cmd_start(args, machine)
    return cmd_info(args, machine)
