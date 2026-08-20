"""Which systems we can fetch. Distro sites rarely publish a stable
"latest.iso" link, so most entries scrape a directory listing instead."""

import re
import urllib.request
from dataclasses import dataclass, field

from .errors import NotFound, BladWirtualki

USER_AGENT = "wirtualka/1.0 (+qemu launcher)"
TIMEOUT = 30


@dataclass(frozen=True)
class Distro:
    slug: str
    name: str
    source: dict = field(default_factory=dict)
    ram: str = "4G"
    disk: str = "40G"
    note: str = ""

    @property
    def manual(self):
        return self.source.get("type") == "manual"


CATALOG = (
    Distro("cachyos", "CachyOS Desktop", {
        "type": "index",
        "url": "https://cdn.cachyos.org/ISO/desktop/",
        "dir_pattern": r"\d{6}/",
        "pattern": r"cachyos-desktop-linux-\d+\.iso",
    }, ram="6G", disk="60G"),
    Distro("cachyos-handheld", "CachyOS Handheld", {
        "type": "index",
        "url": "https://cdn.cachyos.org/ISO/handheld/",
        "dir_pattern": r"\d{6}/",
        "pattern": r"cachyos-handheld-linux-\d+\.iso",
    }, ram="6G", disk="60G"),
    Distro("arch", "Arch Linux", {
        "type": "direct",
        "url": "https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso",
    }, ram="2G", disk="30G"),
    Distro("debian", "Debian netinst", {
        "type": "index",
        "url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/",
        "pattern": r"debian-[\d.]+-amd64-netinst\.iso",
    }, ram="2G", disk="25G"),
    Distro("fedora", "Fedora Workstation", {
        "type": "index",
        "url": "https://dl.fedoraproject.org/pub/fedora/linux/releases/",
        "dir_pattern": r"\d{2}/",
        "subpath": "Workstation/x86_64/iso/",
        "pattern": r"Fedora-Workstation-Live-[\w.-]+\.iso",
    }, ram="4G", disk="40G"),
    Distro("ubuntu", "Ubuntu Desktop LTS", {
        "type": "index",
        "url": "https://releases.ubuntu.com/24.04/",
        "pattern": r"ubuntu-[\d.]+-desktop-amd64\.iso",
    }, ram="4G", disk="40G"),
    Distro("mint", "Linux Mint Cinnamon", {
        "type": "index",
        "url": "https://mirrors.edge.kernel.org/linuxmint/stable/",
        "dir_pattern": r"\d+(?:\.\d+)?/",
        "pattern": r"linuxmint-[\d.]+-cinnamon-64bit\.iso",
    }, ram="4G", disk="40G"),
    Distro("nixos", "NixOS minimal", {
        "type": "direct",
        "url": "https://channels.nixos.org/nixos-unstable/latest-nixos-minimal-x86_64-linux.iso",
    }, ram="2G", disk="30G"),
    Distro("opensuse", "openSUSE Tumbleweed", {
        "type": "direct",
        "url": "https://download.opensuse.org/tumbleweed/iso/openSUSE-Tumbleweed-DVD-x86_64-Current.iso",
    }, ram="4G", disk="40G"),
    Distro("alpine", "Alpine standard", {
        "type": "index",
        "url": "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/",
        "pattern": r"alpine-standard-[\d.]+-x86_64\.iso",
    }, ram="1G", disk="10G"),
    Distro("gentoo", "Gentoo minimal", {
        "type": "index",
        "url": "https://distfiles.gentoo.org/releases/amd64/autobuilds/current-install-amd64-minimal/",
        "pattern": r"install-amd64-minimal-[\dTZ]+\.iso",
    }, ram="4G", disk="50G", note="instalacja recznie, z konsoli"),
    Distro("gentoo-gui", "Gentoo LiveGUI", {
        "type": "index",
        "url": "https://distfiles.gentoo.org/releases/amd64/autobuilds/current-livegui-amd64/",
        "pattern": r"livegui-amd64-[\dTZ]+\.iso",
    }, ram="6G", disk="60G"),
    Distro("nyarch", "Nyarch Linux (GNOME)", {
        "type": "index",
        "url": "https://sourceforge.net/projects/nyarchlinux/files/",
        "pattern": r"Nyarch-Gnome-[\d.]+\.iso",
        "suffix": "/download",
    }, ram="6G", disk="50G", note="Arch dla weeaboo"),
    Distro("nyarch-kde", "Nyarch Linux (KDE)", {
        "type": "index",
        "url": "https://sourceforge.net/projects/nyarchlinux/files/",
        "pattern": r"Nyarch-KDE-[\d.]+\.iso",
        "suffix": "/download",
    }, ram="6G", disk="50G", note="Arch dla weeaboo"),
    Distro("endeavouros", "EndeavourOS", {
        "type": "index",
        "url": "https://mirror.moson.org/endeavouros/iso/",
        "pattern": r"EndeavourOS_[\w.-]+\.iso",
    }, ram="4G", disk="40G"),
    Distro("garuda", "Garuda dr460nized", {
        "type": "direct",
        "url": "https://iso.builds.garudalinux.org/iso/latest/garuda/dr460nized/latest.iso",
        "filename": "garuda-dr460nized-latest.iso",
    }, ram="6G", disk="60G"),
    Distro("archcraft", "Archcraft", {
        "type": "index",
        "url": "https://sourceforge.net/projects/archcraft/files/",
        "pattern": r"archcraft-[\w.-]+-x86_64\.iso",
        "suffix": "/download",
    }, ram="4G", disk="40G", note="rice prosto z pudelka"),
    Distro("artix", "Artix (bez systemd)", {
        "type": "index",
        "url": "https://iso.artixlinux.org/iso/",
        "pattern": r"artix-base-openrc-\d+-x86_64\.iso",
    }, ram="2G", disk="25G"),
    Distro("void", "Void Linux", {
        "type": "index",
        "url": "https://repo-default.voidlinux.org/live/current/",
        "pattern": r"void-live-x86_64-[\d.]+-base\.iso",
    }, ram="2G", disk="25G"),
    Distro("bazzite", "Bazzite (do grania)", {
        "type": "direct",
        "url": "https://download.bazzite.gg/bazzite-stable-amd64.iso",
    }, ram="8G", disk="80G", note="Fedora pod gry i handheldy"),
    Distro("mx", "MX Linux Xfce", {
        "type": "rss",
        "url": "https://sourceforge.net/projects/mx-linux/rss?path=/",
        "pattern": r"https://sourceforge\.net/projects/mx-linux/files/[^<]*MX-\d+_Xfce_x64\.iso/download",
    }, ram="3G", disk="30G"),
    Distro("devuan", "Devuan (bez systemd)", {
        "type": "index",
        "url": "https://files.devuan.org/devuan_daedalus/installer-iso/",
        "pattern": r"devuan_daedalus_[\d.]+_amd64_desktop\.iso",
    }, ram="2G", disk="25G"),
    Distro("kubuntu", "Kubuntu", {
        "type": "index",
        "url": "https://cdimage.ubuntu.com/kubuntu/releases/24.04/release/",
        "pattern": r"kubuntu-[\d.]+-desktop-amd64\.iso",
    }, ram="4G", disk="40G"),
    Distro("lubuntu", "Lubuntu (lekkie)", {
        "type": "index",
        "url": "https://cdimage.ubuntu.com/lubuntu/releases/24.04/release/",
        "pattern": r"lubuntu-[\d.]+-desktop-amd64\.iso",
    }, ram="2G", disk="25G"),
    Distro("xubuntu", "Xubuntu", {
        "type": "index",
        "url": "https://cdimage.ubuntu.com/xubuntu/releases/24.04/release/",
        "pattern": r"xubuntu-[\d.]+-desktop-amd64\.iso",
    }, ram="3G", disk="30G"),
    Distro("ubuntu-server", "Ubuntu Server", {
        "type": "index",
        "url": "https://releases.ubuntu.com/24.04/",
        "pattern": r"ubuntu-[\d.]+-live-server-amd64\.iso",
    }, ram="2G", disk="25G"),
    Distro("debian-live", "Debian Live GNOME", {
        "type": "index",
        "url": "https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/",
        "pattern": r"debian-live-[\d.]+-amd64-gnome\.iso",
    }, ram="4G", disk="30G"),
    Distro("fedora-kde", "Fedora KDE", {
        "type": "index",
        "url": "https://dl.fedoraproject.org/pub/fedora/linux/releases/",
        "dir_pattern": r"\d{2}/",
        "subpath": "KDE/x86_64/iso/",
        "pattern": r"Fedora-KDE-Desktop-Live-[\w.-]+\.iso",
    }, ram="4G", disk="40G"),
    Distro("rocky", "Rocky Linux", {
        "type": "index",
        "url": "https://download.rockylinux.org/pub/rocky/9/isos/x86_64/",
        "pattern": r"Rocky-9[\d.]*-x86_64-minimal\.iso",
    }, ram="2G", disk="25G", note="serwerowa, jak RHEL"),
    Distro("alma", "AlmaLinux", {
        "type": "index",
        "url": "https://repo.almalinux.org/almalinux/9/isos/x86_64/",
        "pattern": r"AlmaLinux-9[\d.]*-x86_64-minimal\.iso",
    }, ram="2G", disk="25G", note="serwerowa, jak RHEL"),
    Distro("freebsd", "FreeBSD", {
        "type": "index",
        "url": "https://download.freebsd.org/releases/amd64/amd64/ISO-IMAGES/",
        "dir_pattern": r"\d+\.\d+/",
        "pattern": r"FreeBSD-[\d.]+-RELEASE-amd64-disc1\.iso",
    }, ram="2G", disk="25G", note="to nie jest Linux"),
    Distro("systemrescue", "SystemRescue", {
        "type": "index",
        "url": "https://sourceforge.net/projects/systemrescuecd/files/sysresccd-x86/",
        "pattern": r"systemrescue-[\d.]+-amd64\.iso",
        "suffix": "/download",
    }, ram="2G", disk="10G", note="ratunkowa, nie instaluje sie"),
    Distro("gparted", "GParted Live", {
        "type": "index",
        "url": "https://sourceforge.net/projects/gparted/files/gparted-live-stable/",
        "pattern": r"gparted-live-[\w.-]+-amd64\.iso",
        "suffix": "/download",
    }, ram="1G", disk="10G", note="do dzielenia dyskow"),
    Distro("clonezilla", "Clonezilla Live", {
        "type": "rss",
        "url": "https://sourceforge.net/projects/clonezilla/rss?path=/clonezilla_live_stable",
        "pattern": r"https://sourceforge\.net/projects/clonezilla/files/[^<]*clonezilla-live-[\w.-]+-amd64\.iso/download",
    }, ram="1G", disk="10G", note="do klonowania dyskow"),
    Distro("kali", "Kali Linux", {
        "type": "index",
        "url": "https://cdimage.kali.org/current/",
        "pattern": r"kali-linux-[\w.]+-installer-amd64\.iso",
    }, ram="4G", disk="40G"),
    Distro("windows", "Windows 11", {
        "type": "manual",
        "info": "Microsoft nie daje stalego linku. Pobierz ISO ze strony microsoft.com "
                "i podaj je przez --iso /sciezka/do/pliku.iso",
    }, ram="8G", disk="80G", note="wymaga --tpm i --secure-boot"),
)

BY_SLUG = {distro.slug: distro for distro in CATALOG}


def get(slug):
    try:
        return BY_SLUG[slug]
    except KeyError:
        raise NotFound(f"nie znam systemu '{slug}' (zobacz: wirtualka --iso-list)") from None


def _fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def _natural_key(text):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


def _newest(page, pattern):
    found = sorted(set(re.findall(pattern, page)), key=lambda name: _natural_key(name.rstrip("/")))
    if not found:
        raise BladWirtualki("nie znalazlem zadnego pliku na tej stronie")
    return found[-1]


def resolve(distro):
    source = distro.source
    kind = source.get("type")

    if kind == "manual":
        raise BladWirtualki(source.get("info", "trzeba pobrac ISO recznie"))
    if kind == "direct":
        return source["url"]
    if kind == "rss":
        # sourceforge nie ma zwyklego listingu, ale wystawia kanal RSS z pelnymi linkami
        links = re.findall(source["pattern"], _fetch(source["url"]))
        if not links:
            raise BladWirtualki("nie znalazlem zadnego pliku w kanale RSS")
        return sorted(set(links), key=_natural_key)[-1]

    base = source["url"]
    if source.get("dir_pattern"):
        base += _newest(_fetch(base), source["dir_pattern"])
    if source.get("subpath"):
        base += source["subpath"]
    return base + _newest(_fetch(base), source["pattern"]) + source.get("suffix", "")
