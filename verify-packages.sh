#!/usr/bin/env bash
# verify-packages.sh
# Run on Debian 13 after:  sudo apt update
# Reports any package name in config/package-lists/*.list.chroot
# that Debian does not know about.

cd "$(dirname "$0")" || exit 1
missing=0

for f in config/package-lists/*.list.chroot; do
  while read -r pkg; do
    case "$pkg" in
      ''|'#'*) continue ;;
    esac
    if ! apt-cache show "$pkg" > /dev/null 2>&1; then
      echo "MISSING: $pkg   (in $f)"
      missing=$((missing + 1))
    fi
  done < "$f"
done

echo "Done. $missing package name(s) not found."
