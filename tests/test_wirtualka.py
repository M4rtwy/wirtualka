import os
import sys
import tempfile
import unittest
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="wirtualka-test-")
os.environ["WIRTUALKA_HOME"] = TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wirtualka import catalog, config, qemu, store, templates  # noqa: E402
from wirtualka.errors import AlreadyExists, NotFound, BladWirtualki  # noqa: E402
from wirtualka.util import format_size_mb, parse_port, parse_size_mb  # noqa: E402


class Sizes(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_size_mb("4G"), 4096)
        self.assertEqual(parse_size_mb("512"), 512)
        self.assertEqual(parse_size_mb("1.5G"), 1536)
        self.assertEqual(parse_size_mb("2T"), 2 * 1024 * 1024)

    def test_back(self):
        self.assertEqual(format_size_mb(8192), "8G")
        self.assertEqual(format_size_mb(768), "768M")

    def test_junk(self):
        for text in ("", "duzo", "4X", "-2G"):
            with self.assertRaises(BladWirtualki):
                parse_size_mb(text)

    def test_ports(self):
        self.assertEqual(parse_port("2222:22"), (2222, 22))
        for text in ("22", "a:b", "70000:22", "0:22"):
            with self.assertRaises(BladWirtualki):
                parse_port(text)


class Config(unittest.TestCase):
    def make(self, **kwargs):
        base = config.VmConfig(name="test")
        for key, value in kwargs.items():
            setattr(base, key, value)
        return base

    def test_roundtrip(self):
        first = self.make(ram_mb=8192, ports=[[2222, 22]])
        second = config.VmConfig.from_dict(first.to_dict())
        self.assertEqual(second.ram_mb, 8192)
        self.assertEqual(second.ports, [[2222, 22]])

    def test_bad_name(self):
        for name in ("", "Duza", "ze spacja", "x" * 40, "../ucieczka"):
            with self.assertRaises(BladWirtualki):
                self.make(name=name).validate()

    def test_bad_values(self):
        with self.assertRaises(BladWirtualki):
            self.make(ram_mb=16).validate()
        with self.assertRaises(BladWirtualki):
            self.make(cpus=0).validate()
        with self.assertRaises(BladWirtualki):
            self.make(display="hologram").validate()
        with self.assertRaises(BladWirtualki):
            self.make(secureboot=True, firmware="bios").validate()
        with self.assertRaises(BladWirtualki):
            self.make(resolution="duzo").validate()

    def test_unknown_field(self):
        with self.assertRaises(BladWirtualki):
            config.VmConfig.from_dict({"name": "test", "kolor": "zielony"})


class Store(unittest.TestCase):
    def setUp(self):
        store.ensure_root()
        for name in store.names():
            store.delete(name)

    def test_create_and_load(self):
        store.create("alfa")
        self.assertIn("alfa", store.names())
        self.assertEqual(store.load("alfa").config.name, "alfa")

    def test_duplicate(self):
        store.create("beta")
        with self.assertRaises(AlreadyExists):
            store.create("beta")

    def test_missing(self):
        with self.assertRaises(NotFound):
            store.load("nieistnieje")

    def test_rename(self):
        store.create("stara")
        store.rename("stara", "nowa")
        self.assertEqual(store.names(), ["nowa"])
        self.assertEqual(store.load("nowa").config.name, "nowa")

    def test_clone_keeps_settings(self):
        machine = store.create("zrodlo")
        machine.config.ram_mb = 2048
        machine.save()
        copy = store.clone("zrodlo", "kopia")
        self.assertEqual(copy.config.ram_mb, 2048)
        self.assertEqual(copy.config.name, "kopia")

    def test_delete_guard(self):
        machine = store.create("gamma")
        machine.path = Path("/tmp")
        with self.assertRaises(BladWirtualki):
            store._guard(machine.path)


class Command(unittest.TestCase):
    def setUp(self):
        store.ensure_root()
        for name in store.names():
            store.delete(name)
        self.machine = store.create("cmd")

    def line(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self.machine.config, key, value)
        return qemu.build(self.machine)

    def test_kvm_and_ram(self):
        args = self.line(ram_mb=4096, cpus=4)
        self.assertIn("accel=kvm", " ".join(args))
        self.assertIn("4096", args)

    def test_no_kvm(self):
        self.assertNotIn("accel=kvm", " ".join(self.line(kvm=False)))

    def test_no_internet(self):
        args = self.line(net="none")
        self.assertIn("-nic", args)
        self.assertIn("none", args)

    def test_ports(self):
        args = " ".join(self.line(net="user", ports=[[2222, 22]]))
        self.assertIn("hostfwd=tcp::2222-:22", args)

    def test_balloon_returns_memory(self):
        self.assertIn("virtio-balloon,free-page-reporting=on", self.line(balloon=True))

    def test_3d(self):
        self.assertIn("virtio-vga-gl,max_outputs=1", self.line(accel3d=True, gpu="virtio"))
        self.assertIn("virtio-vga,max_outputs=1", self.line(accel3d=False, gpu="virtio"))

    def test_resolution(self):
        args = " ".join(self.line(gpu="virtio", resolution="1600x900"))
        self.assertIn("xres=1600,yres=900", args)

    def test_share(self):
        args = " ".join(self.line(shares=[{"tag": "dane", "path": "/tmp", "ro": True}]))
        self.assertIn("mount_tag=dane", args)
        self.assertIn("readonly=on", args)

    def test_iso_boots_first(self):
        args = " ".join(qemu.build(self.machine, iso="/tmp/x.iso"))
        self.assertIn("media=cdrom", args)
        self.assertIn("order=dc", args)

    def test_invalid_config_stops_build(self):
        self.machine.config.cpus = 999
        with self.assertRaises(BladWirtualki):
            qemu.build(self.machine)


class Catalog(unittest.TestCase):
    def test_slugs_unique(self):
        slugs = [distro.slug for distro in catalog.CATALOG]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_sizes_parse(self):
        for distro in catalog.CATALOG:
            parse_size_mb(distro.ram)
            parse_size_mb(distro.disk)

    def test_manual_entry_explains_itself(self):
        with self.assertRaises(BladWirtualki):
            catalog.resolve(catalog.get("windows"))

    def test_unknown(self):
        with self.assertRaises(NotFound):
            catalog.get("temple-os")

    def test_newest_wins(self):
        page = "linuxmint-22-cinnamon-64bit.iso linuxmint-22.3-cinnamon-64bit.iso"
        self.assertEqual(
            catalog._newest(page, r"linuxmint-[\d.]+-cinnamon-64bit\.iso"),
            "linuxmint-22.3-cinnamon-64bit.iso",
        )


class Templates(unittest.TestCase):
    def test_save_and_apply(self):
        source = config.VmConfig(name="wzor", ram_mb=16384, cpus=8)
        templates.save("mocna", source)
        target = config.VmConfig(name="inna")
        templates.apply("mocna", target)
        self.assertEqual(target.ram_mb, 16384)
        self.assertEqual(target.name, "inna")

    def test_missing(self):
        with self.assertRaises(NotFound):
            templates.apply("nieistnieje", config.VmConfig(name="x"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
