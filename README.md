<p align="center">
  <img src="docs/kos-banner.jpg" alt="KrelboyneOS" width="100%">
</p>

# KrelboyneOS

A Debian 13 (trixie) live and installable Linux distribution for developers and security learners, with an Xfce desktop and the tools already set up.

**Status: 0.1 alpha.** It boots and installs in a virtual machine. Real-hardware testing is still ahead.

## What it is

KrelboyneOS is a custom Linux ISO built with [live-build](https://wiki.debian.org/DebianLive). Boot it to try it, or install it to disk with the Calamares installer. The goal is a machine that is ready for software development and security work the moment it finishes installing, with no afternoon of setup first.

It started as a Linux From Scratch idea and became a Debian-based distro, so the focus is on a useful daily workstation.

## What's in it

**Desktop and look**
- Xfce on LightDM with the Arc-Dark theme and Papirus icons
- Dark teal KrelboyneOS branding on the boot menu, installer, login screen and desktop
- conky system monitor on the desktop

**Shell and terminal**
- zsh with Oh My Zsh, autosuggestions, syntax highlighting and a two-line prompt
- zoxide, fzf, ripgrep, fd, bat, tmux, neovim, jq, htop, btop
- Kitty terminal, JetBrainsMono and FiraCode Nerd Fonts

**Development**
- git, git-lfs, lazygit, GitHub CLI
- Python 3 (pip, venv, pipx), Node.js and npm, mise for other languages
- build-essential, cmake, ninja, clang, gdb
- VS Code, Bruno and httpie for APIs
- PostgreSQL and SQLite
- Docker and Docker Compose
- KVM, QEMU, libvirt and virt-manager

**Security**
- nmap, Wireshark and tshark, tcpdump, netcat, mtr, traceroute, whois, dig, iperf3
- OpenVPN and WireGuard
- aircrack-ng, John the Ripper, hashcat, Hydra, sqlmap, gobuster, Nuclei
- Metasploit, BloodHound CE and Burp Suite Community planned: install on demand with the `kos-install-tools` command

**Everyday apps**
- Firefox ESR, GIMP, Claude Desktop

**Building KrelboyneOS from KrelboyneOS**
- live-build, debootstrap, xorriso, squashfs-tools and ImageMagick

**Hardware support**
- Non-free firmware for common Wi-Fi, Bluetooth, sound and graphics hardware (Intel, Realtek)

The security tools are for learning and for testing systems you own or have written permission to test.

## Download

Get the ISO from the [Releases page](https://github.com/grumpy-gaming/KrelboyneOS/releases).

GitHub limits each file to 2 GiB, so the ISO may be split into parts. Join them and check the download like this:

    cat krelboyneos-*.iso.part-* > krelboyneos.iso
    sha256sum -c SHA256SUMS

Write the ISO to a USB stick with a tool such as Ventoy, balenaEtcher or `dd`, then boot from it.

## Try it in a VM

Create a virtual machine with at least 4 GB of RAM, 25 GB of disk and UEFI or BIOS firmware, attach the ISO as its CD-ROM, and boot. Choose Install KrelboyneOS on the desktop to install it.

## Build it yourself

You need a Debian 13 machine with live-build, git and about 20 GB of free disk space.

    git clone https://github.com/grumpy-gaming/KrelboyneOS.git
    cd KrelboyneOS
    sudo lb clean; lb config; sudo lb build

The finished ISO appears in the project folder.

## How the repo is laid out

- `auto/config`: the main live-build settings
- `config/package-lists/`: the packages installed in the image
- `config/hooks/live/`: scripts that run during the build (branding, shell, extra repos, downloads)
- `config/includes.chroot/`: files copied into the image as they are
- `config/bootloaders/`: boot menu artwork
- `docs/`: images for this README

## Where it could go

- Test on real hardware and under UEFI Secure Boot
- Branded GRUB and boot splash screens on the installed system
- Optional lighter and heavier editions, such as a minimal build and a full security build
- A hosted apt repository for KrelboyneOS's own tools
- A proper project website and documentation

## Credits

Built on Debian GNU/Linux, live-build, Calamares, Xfce and the many open source projects listed above. Each keeps its own license.

KrelboyneOS is made by [grumpy-gaming](https://github.com/grumpy-gaming).
