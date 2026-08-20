# generowane z parsera wirtualka
function __wirtualka_machines
    command ls (test -n "$WIRTUALKA_HOME"; and echo $WIRTUALKA_HOME; or echo $HOME/wirtualka)/machines 2>/dev/null
end
complete -c wirtualka -f
complete -c wirtualka -n '__fish_is_first_arg' -a '(__wirtualka_machines)' -d maszyna
complete -c wirtualka -s h -l h -l help -l help -d 'pokaz ta pomoc'
complete -c wirtualka -s n -l new -d 'zrob nowa maszyne i odpal instalator'
complete -c wirtualka -s l -l list -d 'lista maszyn'
complete -c wirtualka -s s -l start -d 'wlacz'
complete -c wirtualka -l stop -d 'wylacz grzecznie'
complete -c wirtualka -l kill -d 'wylacz na chama'
complete -c wirtualka -l restart -d 'wylacz i wlacz'
complete -c wirtualka -l status -d 'czy chodzi i ile bierze'
complete -c wirtualka -s i -l info -d 'wszystkie ustawienia'
complete -c wirtualka -l rm -l delete -d 'skasuj maszyne'
complete -c wirtualka -l clone -d 'kopia (lekka, tylko zmiany zajmuja miejsce)'
complete -c wirtualka -l full-clone -d 'kopia z pelnym dyskiem'
complete -c wirtualka -l rename -d 'zmien nazwe'
complete -c wirtualka -l edit -d 'otworz vm.json w edytorze'
complete -c wirtualka -l no-start -d 'przy --new tylko zrob, nie odpalaj'
complete -c wirtualka -l once -d 'ustawienia tylko na ten jeden raz'
complete -c wirtualka -s d -l distro -d 'system z listy (wirtualka --iso-list)' -x -a 'cachyos cachyos-kde cachyos-cli cachyos-handheld arch debian fedora ubuntu mint nixos opensuse alpine gentoo gentoo-gui kali windows'
complete -c wirtualka -l iso -d 'wlasne ISO'
complete -c wirtualka -l no-iso -d 'odpal bez plyty'
complete -c wirtualka -l iso-list -d 'co umiem pobrac'
complete -c wirtualka -l iso-get -d 'pobierz ISO do cache' -x -a 'cachyos cachyos-kde cachyos-cli cachyos-handheld arch debian fedora ubuntu mint nixos opensuse alpine gentoo gentoo-gui kali windows'
complete -c wirtualka -l iso-cache -d 'co juz mam pobrane'
complete -c wirtualka -l iso-rm -d 'skasuj ISO z cache'
complete -c wirtualka -l ram -d 'np. 8G'
complete -c wirtualka -s c -l cpus
complete -c wirtualka -l disk -d 'rozmiar dysku przy tworzeniu'
complete -c wirtualka -l resize -d 'powieksz dysk'
complete -c wirtualka -l disk-add -d 'dolozy drugi dysk'
complete -c wirtualka -l bus -d 'jak podpiac dysk' -x -a 'virtio sata nvme'
complete -c wirtualka -l cpu-model -d 'np. host albo qemu64'
complete -c wirtualka -l machine -d 'np. q35'
complete -c wirtualka -l kvm
complete -c wirtualka -l no-kvm
complete -c wirtualka -l balloon -d 'oddawaj wolny ram hostowi'
complete -c wirtualka -l no-balloon
complete -c wirtualka -l discard -d 'oddawaj wolne miejsce na dysku'
complete -c wirtualka -l no-discard
complete -c wirtualka -l uefi
complete -c wirtualka -l bios
complete -c wirtualka -l secure-boot
complete -c wirtualka -l no-secure-boot
complete -c wirtualka -l tpm -d 'wirtualny TPM (Windows 11)'
complete -c wirtualka -l no-tpm
complete -c wirtualka -l display -x -a 'gtk sdl spice none curses'
complete -c wirtualka -l gpu -x -a 'virtio qxl vmware std none'
complete -c wirtualka -l vram
complete -c wirtualka -l 3d
complete -c wirtualka -l no-3d
complete -c wirtualka -s r -l resolution -d 'np. 1600x900'
complete -c wirtualka -l headless -d 'bez okna'
complete -c wirtualka -l vnc -d 'podglad przez VNC na :N'
complete -c wirtualka -l audio
complete -c wirtualka -l no-audio
complete -c wirtualka -l no-internet -d 'odetnij siec'
complete -c wirtualka -l net -x -a 'user none'
complete -c wirtualka -l port
complete -c wirtualka -l no-ports -d 'skasuj przekierowania'
complete -c wirtualka -l ssh -d 'skrot na --port 2222:22'
complete -c wirtualka -l mac
complete -c wirtualka -l share -r -F
complete -c wirtualka -l share-ro -r -F
complete -c wirtualka -l unshare
complete -c wirtualka -l clipboard
complete -c wirtualka -l no-clipboard
complete -c wirtualka -l usb
complete -c wirtualka -l snap -d 'zapisz stan dysku'
complete -c wirtualka -l snaps -d 'lista snapshotow'
complete -c wirtualka -l snap-back -d 'wroc do snapshotu'
complete -c wirtualka -l snap-rm -d 'skasuj snapshot'
complete -c wirtualka -l template -d 'uzyj zapisanych ustawien'
complete -c wirtualka -l save-template -d 'zapisz ustawienia jako szablon'
complete -c wirtualka -l template-list
complete -c wirtualka -l template-rm
complete -c wirtualka -l dry-run -d 'pokaz komende qemu i nic nie rob'
complete -c wirtualka -l fg -d 'nie odczepiaj od terminala'
complete -c wirtualka -l log -d 'pokaz koniec logu'
complete -c wirtualka -l monitor -d 'wyslij komende do monitora qemu'
complete -c wirtualka -l usage -d 'ile miejsca zajmuja maszyny i ISO'
complete -c wirtualka -l where -d 'gdzie to wszystko lezy'
complete -c wirtualka -l json -d 'wynik jako JSON'
complete -c wirtualka -s q -l quiet
complete -c wirtualka -s y -l yes -d 'nie pytaj o potwierdzenie'
complete -c wirtualka -s V -l version -d 'show programs version number and exit'
