"""Which systems `wirtualka` can fetch, and how to find their newest ISO.

Distro sites almost never publish a stable "latest.iso" link, so most entries
point at a directory listing and let the resolver pick the newest file.
"""

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
    Distro("cachyos-kde", "CachyOS KDE", {
        "type": "index",
        "url": "https://cdn.cachyos.org/ISO/kde/",
        "dir_pattern": r"\d{6}/",
        "pattern": r"cachyos-kde-linux-\d+\.iso",
    }, ram="6G", disk="60G"),
    Distro("cachyos-cli", "CachyOS CLI", {
        "type": "index",
        "url": "https://cdn.cachyos.org/ISO/cli/",
        "dir_pattern": r"\d{6}/",
        "pattern": r"cachyos-cli-linux-\d+\.iso",
    }, ram="2G", disk="30G"),
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
    """Return the direct download URL for a distro's newest ISO."""
    source = distro.source
    kind = source.get("type")

    if kind == "manual":
        raise BladWirtualki(source.get("info", "trzeba pobrac ISO recznie"))
    if kind == "direct":
        return source["url"]

    base = source["url"]
    if source.get("dir_pattern"):
        base += _newest(_fetch(base), source["dir_pattern"])
    if source.get("subpath"):
        base += source["subpath"]
    return base + _newest(_fetch(base), source["pattern"])
