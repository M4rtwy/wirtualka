<div align="center">
<img src="data/icons/wirtualka.svg" width="120" alt="wirtualka">

# wirtualka — maszyny wirtualne po polsku

**Zrob sobie wirtualnego Linuxa jedna komenda albo jednym klikiem.**
Bez czytania dokumentacji QEMU. Bez libvirta. Bez niczego, co siedzi w tle i zjada komputer.

</div>

---

## Po co to jest

Chcesz sprawdzic Archa, Gentoo albo Kali, ale nie chcesz sobie rozwalic systemu?
Robisz maszyne wirtualna. Tylko ze normalnie trzeba do tego virt-managera, uslugi
`libvirtd` chodzacej caly czas i klikania przez dziesiec ekranow kreatora.

Tutaj to wyglada tak:

```
wirtualka --new -d arch
```

I tyle. Sam pobiera **najnowsze** ISO, robi dysk, odpala instalator w okienku.

Wszystko jest po polsku — komendy, pomoc, komunikaty bledow i okno.

## Instalacja

Potrzebujesz `qemu-desktop` i `edk2-ovmf` (na Arch/CachyOS):

```
sudo pacman -S qemu-desktop edk2-ovmf
git clone https://github.com/m4rtwy/wirtualka.git
cd wirtualka
./install.sh
```

Na Fedorze: `sudo dnf install qemu-kvm edk2-ovmf`, na Debianie/Ubuntu:
`sudo apt install qemu-system-x86 ovmf`.

## Okno, jesli nie lubisz terminala

```
wirtualka --gui
```

albo ikonka **Maszyny wirtualne** w menu programow.

W oknie masz liste maszyn, suwaki na ram i rdzenie, przelacznik internetu,
kopie stanu (mozesz wrocic, jak cos zepsujesz) i pasek postepu przy pobieraniu ISO.

## Komendy, ktore wystarcza na co dzien

```
wirtualka --new -d cachyos          nowa maszyna, sama sciaga najnowsze ISO
wirtualka cachyos --start           wlacz
wirtualka cachyos --stop            wylacz
wirtualka cachyos --no-internet     wlacz bez sieci (dobre do testowania podejrzanych rzeczy)
wirtualka cachyos --no-iso          po instalacji: startuj z dysku, nie z plyty
wirtualka --list                    co mam
wirtualka --usage                   ile to zajmuje miejsca
wirtualka cachyos --rm              skasuj
wirtualka -h                        wszystkie opcje (jest ich ponad 120)
```

Podpowiadanie w **fish** dziala od razu — nazwy maszyn i systemow tez.

## Systemy, ktore pobiera sam

`cachyos` `cachyos-kde` `cachyos-cli` `cachyos-handheld` `arch` `debian` `fedora`
`ubuntu` `mint` `nixos` `opensuse` `alpine` `gentoo` `gentoo-gui` `kali`
`nyarch` `nyarch-kde` (ten memowy Arch dla weeaboo)
oraz `windows` (tu musisz dac wlasne ISO, Microsoft nie daje stalego linku).

Nie ma tu zadnych linkow z wpisanym na sztywno numerem wersji — program wchodzi
na serwer i bierze najnowszy plik. Wlasne ISO tez mozesz podac: `--iso plik.iso`.

## Dlaczego to nic nie zjada, kiedy nie uzywasz

To byl caly punkt tego programu:

- **Zero procesow w tle.** Nie ma zadnej uslugi, ktora czeka. Wylaczona maszyna
  to folder z plikiem `qcow2` — zero ramu, zero procesora.
- **Dysk rosnie w miare uzywania.** `--disk 60G` zajmuje na starcie okolo 200 kB.
- **Ram wraca do hosta.** Kazda maszyna dostaje `virtio-balloon` z
  `free-page-reporting`, wiec gosc sam oddaje wolne strony pamieci.
- **Miejsce tez wraca.** `discard=unmap` — kasujesz cos w maszynie, plik na dysku chudnie.
- **ISO pobiera sie dopiero wtedy, kiedy o nie poprosisz** (i wznawia sie po zerwaniu).

## Sztuczki, ktore ratuja tylek

```
wirtualka --doctor                 sprawdza, czy komputer jest gotowy (KVM, qemu, UEFI, miejsce)
wirtualka arch --temporary         zmiany na dysku znikaja po wylaczeniu - idealne do testow
wirtualka arch --console           caly system w terminalu, bez okienka
wirtualka arch --save-state przed  zapisuje maszyne razem z pamiecia, jak hibernacja
wirtualka arch --load-state przed  i wraca dokladnie tam, gdzie bylo
wirtualka arch --screenshot        zrzut ekranu chodzacej maszyny
wirtualka --all-stop               wylacza wszystko naraz
wirtualka --running                co teraz chodzi i ile je
wirtualka arch --export arch.tar.gz    spakuj maszyne i przenies na inny komputer
wirtualka --import arch.tar.gz         i wypakuj ja tam
wirtualka arch --pin 0-3 --nice 10     zeby maszyna nie przeszkadzala w graniu
wirtualka arch --ssh-into              wejdz po ssh do srodka
```

## Co jeszcze umie

Kopie stanu (`--snap`, `--snap-back`), lekkie klony (`--clone` — kopia zajmuje
tylko to, co sie rozni), wspoldzielone foldery (`--share`), przekierowanie portow
(`--port 2222:22`, `--ssh`), przepuszczanie USB (`--usb`), TPM i Secure Boot dla
Windowsa 11, przyspieszenie 3D (`--3d`), tryb bez ekranu (`--headless`), VNC,
szablony ustawien (`--save-template`), zamrazanie (`--pause`/`--resume`),
wkladanie plyty na zywo (`--cd`), wlasny DNS i nazwe w sieci, uklad klawiatury,
zegar UTC albo lokalny, kilka ekranow naraz, wirtualizacje w wirtualizacji
(`--nested`) i `--dry-run`, jesli chcesz zobaczyc, jaka komende QEMU to wygeneruje.

## Testy

```
python3 -m unittest discover -s tests
```

## Licencja

MIT. Robie to dla ludzi, ktorzy chca pobawic sie Linuxem bez strachu, ze cos zepsuja.
