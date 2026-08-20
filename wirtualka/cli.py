"""Argument parsing only. The work happens in commands.py."""

import argparse

from .constants import DISK_BUSES, DISPLAYS, GPUS, NETS

VERSION = "1.0"

USAGE = """wirtualka [NAZWA] [opcje]

  wirtualka --new -d cachyos            nowa maszyna z najnowszym ISO CachyOS
  wirtualka cachyos --start             odpal
  wirtualka cachyos --no-internet       odpal bez internetu
  wirtualka --list                      co mam
  wirtualka cachyos --ram 8G --cpus 6   zmien sprzet
  wirtualka --iso-list                  jakie systemy umiem pobrac

Nic nie chodzi w tle. Zatrzymana maszyna to tylko folder z plikiem qcow2."""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wirtualka",
        usage=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Maszyny wirtualne na QEMU/KVM, bez zadnego demona w tle.",
        add_help=False,
    )
    # --h sam z siebie bylby niejednoznaczny (--help kontra --headless)
    parser.add_argument("-h", "--h", "-help", "--help", action="help",
                        help="pokaz ta pomoc")
    parser.add_argument("name", nargs="?", help="nazwa maszyny")

    group = parser.add_argument_group("maszyny")
    group.add_argument("-n", "--new", nargs="?", const=True, metavar="NAZWA",
                       help="zrob nowa maszyne i odpal instalator")
    group.add_argument("-l", "--list", action="store_true", help="lista maszyn")
    group.add_argument("-s", "--start", action="store_true", help="wlacz")
    group.add_argument("--stop", action="store_true", help="wylacz grzecznie")
    group.add_argument("--kill", action="store_true", help="wylacz na chama")
    group.add_argument("--restart", action="store_true", help="wylacz i wlacz")
    group.add_argument("--status", action="store_true", help="czy chodzi i ile bierze")
    group.add_argument("-i", "--info", action="store_true", help="wszystkie ustawienia")
    group.add_argument("--rm", "--delete", dest="rm", action="store_true", help="skasuj maszyne")
    group.add_argument("--clone", metavar="NOWA", help="kopia (lekka, tylko zmiany zajmuja miejsce)")
    group.add_argument("--full-clone", action="store_true", help="kopia z pelnym dyskiem")
    group.add_argument("--rename", metavar="NOWA", help="zmien nazwe")
    group.add_argument("--edit", action="store_true", help="otworz vm.json w edytorze")
    group.add_argument("--no-start", action="store_true", help="przy --new tylko zrob, nie odpalaj")
    group.add_argument("--pause", action="store_true", help="zamroz maszyne")
    group.add_argument("--resume", action="store_true", help="odmroz maszyne")
    group.add_argument("--reset", action="store_true", help="reset, jak przycisk w obudowie")
    group.add_argument("--wait", action="store_true", help="czekaj, az maszyna sie wylaczy")
    group.add_argument("--console", action="store_true",
                       help="odpal w terminalu zamiast w okienku")
    group.add_argument("--screenshot", nargs="?", const=True, metavar="PLIK",
                       help="zrzut ekranu chodzacej maszyny")
    group.add_argument("--save-state", metavar="NAZWA",
                       help="zapisz maszyne razem z pamiecia (jak hibernacja)")
    group.add_argument("--load-state", metavar="NAZWA", help="wczytaj zapisany stan")
    group.add_argument("--export", metavar="PLIK", help="spakuj maszyne do .tar.gz")
    group.add_argument("--import", dest="import_file", metavar="PLIK",
                       help="wypakuj maszyne z .tar.gz")
    group.add_argument("--open", action="store_true", help="otworz folder maszyny")
    group.add_argument("--note", metavar="TEKST", help="dopisek, po co ta maszyna jest")
    group.add_argument("--all-stop", action="store_true", help="wylacz wszystkie maszyny")
    group.add_argument("--running", action="store_true", help="pokaz tylko chodzace")
    group.add_argument("--doctor", action="store_true",
                       help="sprawdz, czy komputer jest gotowy na maszyny wirtualne")
    group.add_argument("--once", action="store_true", help="ustawienia tylko na ten jeden raz")

    group = parser.add_argument_group("systemy i ISO")
    group.add_argument("-d", "--distro", metavar="ID", help="system z listy (wirtualka --iso-list)")
    group.add_argument("--iso", metavar="PLIK", help="wlasne ISO")
    group.add_argument("--no-iso", action="store_true", help="odpal bez plyty")
    group.add_argument("--iso-list", action="store_true", help="co umiem pobrac")
    group.add_argument("--iso-get", metavar="ID", help="pobierz ISO do cache")
    group.add_argument("--iso-cache", action="store_true", help="co juz mam pobrane")
    group.add_argument("--iso-rm", metavar="NAZWA", help="skasuj ISO z cache")

    group = parser.add_argument_group("sprzet")
    group.add_argument("--ram", metavar="ROZMIAR", help="np. 8G")
    group.add_argument("-c", "--cpus", type=int, metavar="N")
    group.add_argument("--disk", metavar="ROZMIAR", help="rozmiar dysku przy tworzeniu")
    group.add_argument("--resize", metavar="ROZMIAR", help="powieksz dysk")
    group.add_argument("--disk-add", metavar="ROZMIAR", help="dolozy drugi dysk")
    group.add_argument("--bus", choices=DISK_BUSES, help="jak podpiac dysk")
    group.add_argument("--cpu-model", metavar="MODEL", help="np. host albo qemu64")
    group.add_argument("--machine", metavar="TYP", help="np. q35")
    group.add_argument("--kvm", dest="kvm", action="store_true", default=None)
    group.add_argument("--no-kvm", dest="kvm", action="store_false")
    group.add_argument("--balloon", dest="balloon", action="store_true", default=None,
                       help="oddawaj wolny ram hostowi")
    group.add_argument("--no-balloon", dest="balloon", action="store_false")
    group.add_argument("--discard", dest="discard", action="store_true", default=None,
                       help="oddawaj wolne miejsce na dysku")
    group.add_argument("--no-discard", dest="discard", action="store_false")
    group.add_argument("--uefi", dest="firmware", action="store_const", const="uefi")
    group.add_argument("--bios", dest="firmware", action="store_const", const="bios")
    group.add_argument("--secure-boot", dest="secureboot", action="store_true", default=None)
    group.add_argument("--no-secure-boot", dest="secureboot", action="store_false")
    group.add_argument("--temporary", "--na-chwile", dest="temporary", action="store_true",
                       default=None, help="zmiany na dysku znikaja po wylaczeniu")
    group.add_argument("--no-temporary", dest="temporary", action="store_false")
    group.add_argument("--fast-disk", dest="fast_disk", action="store_true", default=None,
                       help="szybszy zapis, ale przy zaniku pradu dysk moze paść")
    group.add_argument("--no-fast-disk", dest="fast_disk", action="store_false")
    group.add_argument("--nested", dest="nested", action="store_true", default=None,
                       help="maszyna wirtualna w maszynie wirtualnej")
    group.add_argument("--no-nested", dest="nested", action="store_false")
    group.add_argument("--pin", metavar="RDZENIE", help="np. 0-3, przypisz konkretne rdzenie")
    group.add_argument("--nice", type=int, metavar="N",
                       help="priorytet, od -20 do 19 (wyzej = mniej przeszkadza)")
    group.add_argument("--keyboard", metavar="UKLAD", help="np. pl")
    group.add_argument("--rtc", choices=("localtime", "utc"), help="zegar maszyny")
    group.add_argument("--sound-model", choices=("hda", "ac97", "es1370"))
    group.add_argument("--disk-rm", type=int, metavar="N", help="usun dolozony dysk numer N")
    group.add_argument("--tpm", dest="tpm", action="store_true", default=None,
                       help="wirtualny TPM (Windows 11)")
    group.add_argument("--no-tpm", dest="tpm", action="store_false")

    group = parser.add_argument_group("ekran")
    group.add_argument("--display", choices=DISPLAYS)
    group.add_argument("--gpu", choices=GPUS)
    group.add_argument("--vram", type=int, metavar="MB")
    group.add_argument("--3d", dest="accel3d", action="store_true", default=None)
    group.add_argument("--no-3d", dest="accel3d", action="store_false")
    group.add_argument("-r", "--resolution", metavar="WxH", help="np. 1600x900")
    group.add_argument("--headless", action="store_true", help="bez okna")
    group.add_argument("--vnc", type=int, metavar="N", help="podglad przez VNC na :N")
    group.add_argument("--fit", dest="fit", action="store_true", default=None,
                       help="dopasuj obraz do okna")
    group.add_argument("--no-fit", dest="fit", action="store_false")
    group.add_argument("--fullscreen", action="store_true",
                       help="pelny ekran (wyjscie: ctrl+alt+f)")
    group.add_argument("--screens", type=int, metavar="N", help="ile ekranow (1-4)")
    group.add_argument("--audio", dest="audio", action="store_true", default=None)
    group.add_argument("--no-audio", dest="audio", action="store_false")

    group = parser.add_argument_group("siec")
    group.add_argument("--no-internet", action="store_true", help="odetnij siec")
    group.add_argument("--net", choices=NETS)
    group.add_argument("--port", action="append", metavar="HOST:GOSC", default=[])
    group.add_argument("--no-ports", action="store_true", help="skasuj przekierowania")
    group.add_argument("--ssh", action="store_true", help="skrot na --port 2222:22")
    group.add_argument("--mac", metavar="ADRES")
    group.add_argument("--dns", metavar="IP", help="wlasny serwer DNS w maszynie")
    group.add_argument("--hostname", metavar="NAZWA", help="nazwa maszyny widziana w sieci")
    group.add_argument("--port-udp", action="append", metavar="HOST:GOSC", default=[])
    group.add_argument("--ssh-into", action="store_true", help="polacz sie po ssh")
    group.add_argument("--cd", metavar="PLIK", help="wloz plyte (mozna na zywo)")
    group.add_argument("--eject", action="store_true", help="wyjmij plyte na zywo")

    group = parser.add_argument_group("foldery i usb")
    group.add_argument("--share", action="append", metavar="FOLDER", default=[])
    group.add_argument("--share-ro", action="append", metavar="FOLDER", default=[])
    group.add_argument("--unshare", metavar="TAG")
    group.add_argument("--clipboard", dest="clipboard", action="store_true", default=None)
    group.add_argument("--no-clipboard", dest="clipboard", action="store_false")
    group.add_argument("--usb", action="append", metavar="VID:PID", default=[])

    group = parser.add_argument_group("snapshoty")
    group.add_argument("--snap", metavar="NAZWA", help="zapisz stan dysku")
    group.add_argument("--snaps", action="store_true", help="lista snapshotow")
    group.add_argument("--snap-back", metavar="NAZWA", help="wroc do snapshotu")
    group.add_argument("--snap-rm", metavar="NAZWA", help="skasuj snapshot")

    group = parser.add_argument_group("szablony")
    group.add_argument("--template", metavar="NAZWA", help="uzyj zapisanych ustawien")
    group.add_argument("--save-template", metavar="NAZWA", help="zapisz ustawienia jako szablon")
    group.add_argument("--template-list", action="store_true")
    group.add_argument("--template-rm", metavar="NAZWA")

    group = parser.add_argument_group("reszta")
    group.add_argument("--gui", "--okno", dest="gui", action="store_true",
                       help="otworz okno zamiast pisac komendy")
    group.add_argument("--dry-run", action="store_true", help="pokaz komende qemu i nic nie rob")
    group.add_argument("--fg", action="store_true", help="nie odczepiaj od terminala")
    group.add_argument("--log", action="store_true", help="pokaz koniec logu")
    group.add_argument("--monitor", metavar="KOMENDA", help="wyslij komende do monitora qemu")
    group.add_argument("--usage", action="store_true", help="ile miejsca zajmuja maszyny i ISO")
    group.add_argument("--where", action="store_true", help="gdzie to wszystko lezy")
    group.add_argument("--json", action="store_true", help="wynik jako JSON")
    group.add_argument("-q", "--quiet", action="store_true")
    group.add_argument("-y", "--yes", action="store_true", help="nie pytaj o potwierdzenie")
    group.add_argument("-V", "--version", action="version", version=f"wirtualka {VERSION}")
    return parser


def main(argv=None):
    from .commands import dispatch

    parser = build_parser()
    args = parser.parse_args(argv)
    return dispatch(args, parser)
