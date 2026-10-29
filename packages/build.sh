#!/bin/sh
# Build the krelboyneos-tools .deb from packages/krelboyneos-tools.
#   packages/build.sh            writes packages/dist/krelboyneos-tools_<version>_all.deb
# auto/build runs it before every ISO build and copies the result into
# config/packages.chroot, so the ISO installs the same package that the
# KrelboyneOS apt repository serves.
set -e

cd "$(dirname "$0")"
src=krelboyneos-tools
version=$(sed -n 's/^Version: //p' "$src/DEBIAN/control")
out="dist/krelboyneos-tools_${version}_all.deb"

# Build from a copy so the repo's control file stays free of the computed size
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -a "$src" "$work/pkg"
# Claude Code's sandbox leaves .claude/.cc-writes folders in directories it works in;
# never ship one (0.1.5.2 to 0.1.6 installed an empty /.claude this way)
find "$work/pkg" -name .claude -prune -exec rm -rf {} +
size=$(du -sk --exclude=DEBIAN "$work/pkg" | cut -f1)
echo "Installed-Size: $size" >> "$work/pkg/DEBIAN/control"
# Standard permissions whatever the builder's umask: 755 folders and programs, 644 the rest
find "$work/pkg" -type d -exec chmod 755 {} +
find "$work/pkg" -type f -exec chmod 644 {} +
chmod 755 "$work/pkg/usr/bin/"* "$work/pkg/DEBIAN/postinst" "$work/pkg/DEBIAN/postrm"

# Reproducible: the same sources always give the same .deb, so the copy built into
# the ISO matches the one in the apt repository byte for byte (apt refuses two
# different files with one version). All times come from the package's last commit.
# (safe.directory: the ISO build runs this as root on a repo owned by the user)
SOURCE_DATE_EPOCH=$(git -c safe.directory='*' log -1 --format=%ct -- "$src")
[ -n "$SOURCE_DATE_EPOCH" ] || { echo "build.sh: cannot read the last commit time from git" >&2; exit 1; }
export SOURCE_DATE_EPOCH
find "$work/pkg" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

mkdir -p dist
dpkg-deb --root-owner-group --build "$work/pkg" "$out"
echo "Built $out"
