#!/bin/sh
# Copy Stevie (the KOS assistant) into the krelboyneos-tools package.
#   packages/sync-stevie.sh [path to krel-assistant checkout]   (default ~/krel-assistant)
# Takes the checkout's last commit (not uncommitted changes) and records which
# commit it was, so the package always matches something on GitHub.
set -e

src=${1:-$HOME/krel-assistant}
dest="$(dirname "$0")/krelboyneos-tools/usr/lib/krelboyneos-tools"
commit=$(git -C "$src" rev-parse --short HEAD)

rm -rf "$dest/stevie"
mkdir -p "$dest"
git -C "$src" archive HEAD stevie | tar -x -C "$dest"
echo "$commit" > "$dest/stevie/SOURCE_COMMIT"
echo "Copied Stevie from krel-assistant $commit into $dest/stevie"
