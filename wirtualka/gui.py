"""Okno na to samo, co robi komenda wirtualka."""

import threading

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import catalog, disk, iso, run, store  # noqa: E402
from .constants import DISPLAYS, GPUS, OVMF_VARS  # noqa: E402
from .errors import BladWirtualki  # noqa: E402
from .util import format_size_mb, human_bytes, parse_port, parse_size_mb  # noqa: E402

APP_ID = "dev.m4rtwy.wirtualka"
DISPLAY_NAMES = {"gtk": "Okno (GTK)", "sdl": "Okno (SDL)", "spice": "SPICE",
                 "none": "Bez ekranu", "curses": "W terminalu"}
GPU_NAMES = {"virtio": "virtio (najlepsza)", "qxl": "QXL", "vmware": "VMware",
             "std": "Zwykla", "none": "Brak"}


def in_thread(work, done):
    def runner():
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - trafia do dymka w oknie
            GLib.idle_add(done, None, error)
        else:
            GLib.idle_add(done, result, None)

    threading.Thread(target=runner, daemon=True).start()


class NewMachineDialog(Adw.Dialog):
    def __init__(self, on_create):
        super().__init__(title="Nowa maszyna", content_width=460)
        self.on_create = on_create

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Co instalujemy")

        self.distros = [d for d in catalog.CATALOG]
        labels = [f"{d.name}" for d in self.distros]
        self.distro_row = Adw.ComboRow(title="System",
                                       model=Gtk.StringList.new(labels))
        self.distro_row.connect("notify::selected", self.on_distro)
        group.add(self.distro_row)

        self.name_row = Adw.EntryRow(title="Nazwa")
        self.name_row.set_text(self.distros[0].slug)
        group.add(self.name_row)

        self.own_iso = None
        self.iso_row = Adw.ActionRow(title="Wlasny plik ISO", subtitle="nie wybrano",
                                     visible=False)
        pick = Gtk.Button(label="Wybierz", valign=Gtk.Align.CENTER)
        pick.connect("clicked", self.on_pick_iso)
        self.iso_row.add_suffix(pick)
        group.add(self.iso_row)
        page.add(group)

        hardware = Adw.PreferencesGroup(title="Sprzet")
        self.ram_row = Adw.SpinRow.new_with_range(1, 32, 1)
        self.ram_row.set_title("Pamiec RAM")
        self.ram_row.set_subtitle("w gigabajtach")
        hardware.add(self.ram_row)

        self.cpu_row = Adw.SpinRow.new_with_range(1, 28, 1)
        self.cpu_row.set_title("Rdzenie procesora")
        hardware.add(self.cpu_row)

        self.disk_row = Adw.SpinRow.new_with_range(5, 500, 5)
        self.disk_row.set_title("Dysk")
        self.disk_row.set_subtitle("w gigabajtach, rosnie w miare uzywania")
        hardware.add(self.disk_row)
        page.add(hardware)

        options = Adw.PreferencesGroup(title="Opcje")
        self.net_row = Adw.SwitchRow(title="Internet", active=True)
        options.add(self.net_row)
        self.start_row = Adw.SwitchRow(title="Odpal od razu po zrobieniu", active=True)
        options.add(self.start_row)
        page.add(options)

        create = Gtk.Button(label="Zrob maszyne", css_classes=["suggested-action", "pill"],
                            margin_top=12, margin_bottom=12, halign=Gtk.Align.CENTER)
        create.connect("clicked", self.on_click)
        page.add(self._wrap(create))

        header = Adw.HeaderBar(show_end_title_buttons=True)
        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(Gtk.ScrolledWindow(child=page, vexpand=True))
        self.set_child(view)
        self.on_distro(self.distro_row, None)

    def _wrap(self, widget):
        group = Adw.PreferencesGroup()
        group.add(widget)
        return group

    def on_distro(self, row, _param):
        distro = self.distros[row.get_selected()]
        self.name_row.set_text(distro.slug)
        self.ram_row.set_value(parse_size_mb(distro.ram) / 1024)
        self.cpu_row.set_value(4)
        self.disk_row.set_value(parse_size_mb(distro.disk) / 1024)
        self.iso_row.set_visible(distro.manual)

    def on_pick_iso(self, _button):
        dialog = Gtk.FileDialog(title="Wskaz plik ISO")

        def picked(source, result):
            try:
                chosen = source.open_finish(result)
            except GLib.Error:
                return
            self.own_iso = chosen.get_path()
            self.iso_row.set_subtitle(chosen.get_basename())

        dialog.open(self.get_root(), None, picked)

    def on_click(self, _button):
        distro = self.distros[self.distro_row.get_selected()]
        self.on_create({
            "iso": self.own_iso,
            "name": self.name_row.get_text().strip(),
            "distro": distro,
            "ram_mb": int(self.ram_row.get_value() * 1024),
            "cpus": int(self.cpu_row.get_value()),
            "disk_mb": int(self.disk_row.get_value() * 1024),
            "net": "user" if self.net_row.get_active() else "none",
            "start": self.start_row.get_active(),
        })
        self.close()


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Maszyny wirtualne",
                         default_width=1000, default_height=700)
        self.machines = []
        self.selected = None

        self.toasts = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView(min_sidebar_width=260, max_sidebar_width=320)
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        self.split.set_sidebar(self._sidebar())
        self.split.set_content(Adw.NavigationPage(title="Maszyna", child=Adw.ToolbarView()))

        self.reload()
        GLib.timeout_add_seconds(3, self._tick)

    # ---------- sidebar ----------

    def _sidebar(self):
        header = Adw.HeaderBar()
        new_button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Nowa maszyna")
        new_button.connect("clicked", self.on_new)
        header.pack_start(new_button)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Odswiez")
        refresh.connect("clicked", lambda *_: self.reload())
        header.pack_end(refresh)

        self.list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.list.connect("row-selected", self.on_select)

        self.progress = Gtk.ProgressBar(show_text=True, visible=False,
                                        margin_start=12, margin_end=12, margin_bottom=12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Gtk.ScrolledWindow(child=self.list, vexpand=True))
        box.append(self.progress)

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(box)
        return Adw.NavigationPage(title="Maszyny", child=view)

    def reload(self, keep=None):
        keep = keep or (self.selected.name if self.selected else None)
        self.list.remove_all()
        self.machines = store.all_machines()
        for machine in self.machines:
            running = run.is_running(machine)
            row = Adw.ActionRow(title=machine.name,
                                subtitle=machine.config.distro or "wlasne ISO")
            dot = Gtk.Image(icon_name="media-playback-start-symbolic" if running
                            else "media-playback-stop-symbolic")
            dot.add_css_class("success" if running else "dim-label")
            row.add_prefix(dot)
            self.list.append(row)
        if not self.machines:
            self.show_empty()
            return
        index = next((i for i, m in enumerate(self.machines) if m.name == keep), 0)
        self.list.select_row(self.list.get_row_at_index(index))

    def _tick(self):
        for index, machine in enumerate(self.machines):
            row = self.list.get_row_at_index(index)
            if not row:
                continue
            running = run.is_running(machine)
            icon = row.get_first_child().get_first_child().get_first_child()
            if isinstance(icon, Gtk.Image):
                icon.set_from_icon_name("media-playback-start-symbolic" if running
                                        else "media-playback-stop-symbolic")
        if self.selected:
            self.state_row.set_subtitle(self._state_text(self.selected))
            self._sync_buttons(self.selected)
        return True

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=4))

    def fail(self, error):
        self.toast(str(error) if isinstance(error, BladWirtualki) else f"cos poszlo nie tak: {error}")

    # ---------- details ----------

    def show_empty(self):
        self.selected = None
        page = Adw.StatusPage(title="Nie masz jeszcze zadnej maszyny",
                              description="Kliknij plus w lewym gornym rogu.",
                              icon_name="computer-symbolic")
        button = Gtk.Button(label="Zrob pierwsza maszyne",
                            css_classes=["suggested-action", "pill"], halign=Gtk.Align.CENTER)
        button.connect("clicked", self.on_new)
        page.set_child(button)
        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar())
        view.set_content(page)
        self.split.set_content(Adw.NavigationPage(title="Maszyny", child=view))

    def on_select(self, _list, row):
        if row is None:
            return
        index = row.get_index()
        if 0 <= index < len(self.machines):
            self.selected = self.machines[index]
            self.split.set_content(self._details(self.selected))

    def _state_text(self, machine):
        if run.is_running(machine):
            return (f"chodzi, {run.rss_mb(machine)} MB ramu, "
                    f"{run.uptime(machine) // 60} min")
        return "wylaczona - nie bierze ani ramu, ani procesora"

    def _sync_buttons(self, machine):
        running = run.is_running(machine)
        self.start_button.set_sensitive(not running)
        self.stop_button.set_sensitive(running)

    def _details(self, machine):
        config = machine.config
        page = Adw.PreferencesPage()

        state = Adw.PreferencesGroup(title="Stan")
        self.state_row = Adw.ActionRow(title=machine.name, subtitle=self._state_text(machine))
        state.add(self.state_row)
        page.add(state)

        hardware = Adw.PreferencesGroup(title="Sprzet")
        ram = Adw.SpinRow.new_with_range(1, 32, 1)
        ram.set_title("Pamiec RAM (GB)")
        ram.set_value(config.ram_mb / 1024)
        ram.connect("notify::value", self._setter(machine, "ram_mb",
                                                  lambda row: int(row.get_value() * 1024)))
        hardware.add(ram)

        cpus = Adw.SpinRow.new_with_range(1, 28, 1)
        cpus.set_title("Rdzenie")
        cpus.set_value(config.cpus)
        cpus.connect("notify::value", self._setter(machine, "cpus",
                                                   lambda row: int(row.get_value())))
        hardware.add(cpus)

        used = human_bytes(disk.used_bytes(machine.disk)) if machine.disk.exists() else "0"
        disk_row = Adw.ActionRow(title="Dysk",
                                 subtitle=f"{format_size_mb(config.disk_mb)}, zajete {used}")
        grow = Gtk.Button(label="Powieksz", valign=Gtk.Align.CENTER)
        grow.connect("clicked", lambda *_: self.on_resize(machine))
        disk_row.add_suffix(grow)
        hardware.add(disk_row)
        page.add(hardware)

        screen = Adw.PreferencesGroup(title="Ekran i dzwiek")
        display = Adw.ComboRow(title="Ekran",
                               model=Gtk.StringList.new([DISPLAY_NAMES[d] for d in DISPLAYS]))
        display.set_selected(DISPLAYS.index(config.display))
        display.connect("notify::selected", self._setter(
            machine, "display", lambda row: DISPLAYS[row.get_selected()]))
        screen.add(display)

        gpu = Adw.ComboRow(title="Karta graficzna",
                           model=Gtk.StringList.new([GPU_NAMES[g] for g in GPUS]))
        gpu.set_selected(GPUS.index(config.gpu))
        gpu.connect("notify::selected", self._setter(
            machine, "gpu", lambda row: GPUS[row.get_selected()]))
        screen.add(gpu)

        accel = Adw.SwitchRow(title="Przyspieszenie 3D", active=config.accel3d)
        accel.connect("notify::active", self._setter(machine, "accel3d",
                                                     lambda row: row.get_active()))
        screen.add(accel)

        audio = Adw.SwitchRow(title="Dzwiek", active=config.audio)
        audio.connect("notify::active", self._setter(machine, "audio",
                                                     lambda row: row.get_active()))
        screen.add(audio)
        page.add(screen)

        network = Adw.PreferencesGroup(title="Siec")
        internet = Adw.SwitchRow(title="Internet",
                                 subtitle="wylacz, jesli testujesz cos podejrzanego",
                                 active=config.net != "none")
        internet.connect("notify::active", self._setter(
            machine, "net", lambda row: "user" if row.get_active() else "none"))
        network.add(internet)

        ports = Adw.EntryRow(title="Przekierowane porty")
        ports.set_text(", ".join(f"{h}:{g}" for h, g in config.ports))
        ports.connect("apply", lambda row: self.on_ports(machine, row))
        ports.set_show_apply_button(True)
        network.add(ports)
        page.add(network)

        extras = Adw.PreferencesGroup(title="Reszta")
        clipboard = Adw.SwitchRow(title="Wspolny schowek", active=config.clipboard)
        clipboard.connect("notify::active", self._setter(machine, "clipboard",
                                                         lambda row: row.get_active()))
        extras.add(clipboard)

        share = Adw.ActionRow(title="Wspoldzielone foldery",
                              subtitle=", ".join(s["path"] for s in config.shares) or "brak")
        add_share = Gtk.Button(label="Dodaj", valign=Gtk.Align.CENTER)
        add_share.connect("clicked", lambda *_: self.on_share(machine))
        share.add_suffix(add_share)
        extras.add(share)

        if config.iso:
            plate = Adw.ActionRow(title="Wlozona plyta", subtitle=config.iso.split("/")[-1])
            eject = Gtk.Button(label="Wyjmij", valign=Gtk.Align.CENTER,
                               tooltip_text="Po instalacji systemu")
            eject.connect("clicked", lambda *_: self.on_eject(machine))
            plate.add_suffix(eject)
            extras.add(plate)
        page.add(extras)

        snaps = Adw.PreferencesGroup(title="Kopie stanu")
        for name, _when, _size in (disk.snapshots(machine.disk) if machine.disk.exists() else []):
            row = Adw.ActionRow(title=name)
            back = Gtk.Button(label="Wroc tutaj", valign=Gtk.Align.CENTER)
            back.connect("clicked", lambda _b, n=name: self.on_snap_back(machine, n))
            row.add_suffix(back)
            snaps.add(row)
        make_snap = Gtk.Button(label="Zapisz obecny stan", valign=Gtk.Align.CENTER)
        make_snap.connect("clicked", lambda *_: self.on_snap(machine))
        snap_row = Adw.ActionRow(title="Nowa kopia",
                                 subtitle="mozesz do niej wrocic, jak cos zepsujesz")
        snap_row.add_suffix(make_snap)
        snaps.add(snap_row)
        page.add(snaps)

        danger = Adw.PreferencesGroup()
        delete = Gtk.Button(label="Skasuj maszyne", css_classes=["destructive-action", "pill"],
                            halign=Gtk.Align.CENTER, margin_top=6, margin_bottom=18)
        delete.connect("clicked", lambda *_: self.on_delete(machine))
        danger.add(delete)
        page.add(danger)

        header = Adw.HeaderBar()
        self.start_button = Gtk.Button(label="Wlacz", css_classes=["suggested-action"])
        self.start_button.connect("clicked", lambda *_: self.on_start(machine))
        header.pack_start(self.start_button)
        self.stop_button = Gtk.Button(label="Wylacz")
        self.stop_button.connect("clicked", lambda *_: self.on_stop(machine))
        header.pack_start(self.stop_button)
        self._sync_buttons(machine)

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(Gtk.ScrolledWindow(child=page, vexpand=True))
        return Adw.NavigationPage(title=machine.name, child=view)

    def _setter(self, machine, field, read):
        def changed(row, *_):
            setattr(machine.config, field, read(row))
            try:
                machine.save()
            except BladWirtualki as error:
                self.fail(error)
        return changed

    # ---------- actions ----------

    def on_new(self, *_):
        NewMachineDialog(self.create_machine).present(self)

    def create_machine(self, spec):
        distro = spec["distro"]
        if distro.manual and not spec.get("iso"):
            return self.toast("ten system wymaga wskazania wlasnego pliku ISO")
        self.progress.set_visible(True)
        self.progress.set_text(f"pobieram {distro.name}...")
        self.progress.set_fraction(0)

        def report(done, total):
            if total:
                GLib.idle_add(self.progress.set_fraction, done / total)

        def work():
            media = spec.get("iso")
            if media is None and not distro.manual:
                media = iso.ensure(distro.slug, on_progress=report)
            store.ensure_root()
            machine = store.create(spec["name"], distro)
            config = machine.config
            config.ram_mb = spec["ram_mb"]
            config.cpus = spec["cpus"]
            config.disk_mb = spec["disk_mb"]
            config.net = spec["net"]
            if media:
                config.iso = str(media)
                config.boot = "cd"
            machine.save()
            disk.create(machine.disk, config.disk_mb)
            if config.firmware == "uefi" and not machine.nvram.exists():
                machine.nvram.write_bytes(OVMF_VARS.read_bytes())
            if spec["start"]:
                run.start(machine, iso=media)
            return machine

        def done(machine, error):
            self.progress.set_visible(False)
            if error:
                return self.fail(error)
            self.reload(keep=machine.name)
            self.toast(f"{machine.name} gotowa")

        in_thread(work, done)

    def on_start(self, machine):
        media = machine.config.iso or None
        self.start_button.set_sensitive(False)
        in_thread(lambda: run.start(machine, iso=media),
                  lambda pid, error: self.fail(error) if error
                  else self.toast(f"{machine.name} wystartowala"))

    def on_stop(self, machine):
        self.stop_button.set_sensitive(False)
        in_thread(lambda: run.stop(machine),
                  lambda _ok, error: self.fail(error) if error
                  else self.toast(f"{machine.name} zatrzymana"))

    def on_eject(self, machine):
        machine.config.iso = ""
        machine.config.boot = "auto"
        machine.save()
        self.reload(keep=machine.name)
        self.split.set_content(self._details(machine))
        self.toast("plyta wyjeta - teraz startuje z dysku")

    def on_ports(self, machine, row):
        try:
            pairs = [list(parse_port(item.strip()))
                     for item in row.get_text().split(",") if item.strip()]
        except BladWirtualki as error:
            return self.fail(error)
        machine.config.ports = pairs
        machine.save()
        self.toast("porty zapisane")

    def on_share(self, machine):
        dialog = Gtk.FileDialog(title="Ktory folder udostepnic?")

        def picked(source, result):
            try:
                folder = source.select_folder_finish(result)
            except GLib.Error:
                return
            path = folder.get_path()
            tag = "".join(c for c in folder.get_basename().lower() if c.isalnum())[:16] or "share"
            machine.config.shares = [s for s in machine.config.shares if s["tag"] != tag]
            machine.config.shares.append({"tag": tag, "path": path, "ro": False})
            machine.save()
            self.split.set_content(self._details(machine))
            self.toast(f"w maszynie zamontujesz to jako '{tag}'")

        dialog.select_folder(self, None, picked)

    def _ask_text(self, title, body, placeholder, on_ok):
        dialog = Adw.AlertDialog(heading=title, body=body)
        entry = Gtk.Entry(placeholder_text=placeholder, margin_top=6)
        dialog.set_extra_child(entry)
        dialog.add_response("nie", "Anuluj")
        dialog.add_response("tak", "Zrob")
        dialog.set_response_appearance("tak", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda _d, answer: answer == "tak"
                       and on_ok(entry.get_text().strip()))
        dialog.present(self)

    def on_snap(self, machine):
        def make(name):
            if not name:
                return
            try:
                disk.snapshot_create(machine.disk, name)
            except BladWirtualki as error:
                return self.fail(error)
            self.split.set_content(self._details(machine))
            self.toast(f"kopia '{name}' zapisana")

        self._ask_text("Zapisac obecny stan?",
                       "Bedziesz mogl tu wrocic, jak cos sie zepsuje.", "np. czysty-system", make)

    def on_snap_back(self, machine, name):
        if run.is_running(machine):
            return self.toast("najpierw wylacz maszyne")
        try:
            disk.snapshot_restore(machine.disk, name)
        except BladWirtualki as error:
            return self.fail(error)
        self.toast(f"wrocone do '{name}'")

    def on_resize(self, machine):
        def grow(text):
            try:
                disk.resize(machine.disk, parse_size_mb(text))
            except BladWirtualki as error:
                return self.fail(error)
            machine.config.disk_mb = parse_size_mb(text)
            machine.save()
            self.split.set_content(self._details(machine))
            self.toast("dysk powiekszony")

        self._ask_text("O ile powiekszyc dysk?",
                       "Podaj docelowy rozmiar, np. 80G. Zmniejszyc sie nie da.", "80G", grow)

    def on_delete(self, machine):
        if run.is_running(machine):
            return self.toast("najpierw wylacz maszyne")
        used = human_bytes(disk.used_bytes(machine.disk)) if machine.disk.exists() else "0"
        dialog = Adw.AlertDialog(
            heading=f"Skasowac '{machine.name}'?",
            body=f"Dysk zajmuje {used}. Tego sie nie da cofnac.")
        dialog.add_response("nie", "Zostaw")
        dialog.add_response("tak", "Skasuj")
        dialog.set_response_appearance("tak", Adw.ResponseAppearance.DESTRUCTIVE)

        def answered(_dialog, answer):
            if answer != "tak":
                return
            try:
                store.delete(machine.name)
            except BladWirtualki as error:
                return self.fail(error)
            self.selected = None
            self.reload()
            self.toast("skasowane")

        dialog.connect("response", answered)
        dialog.present(self)


class AplikacjaWirtualka(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        store.ensure_root()
        window = self.props.active_window or Window(self)
        window.present()


def main():
    return AplikacjaWirtualka().run([])
