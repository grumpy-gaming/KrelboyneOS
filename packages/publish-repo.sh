#!/bin/sh
# Publish the KrelboyneOS apt repository: https://dl.krelboyneos.org/apt
#   packages/publish-repo.sh            build, sign (asks for the key's passphrase) and upload
#   packages/publish-repo.sh --no-upload  build and sign only, into packages/repo
# Holds the current krelboyneos-tools only, like the ISO downloads: one release at a time.
set -e

KEY=6E4FBFF22E772BF3172D90F627972B3922E08260
REMOTE=r2:krelboyneos/apt

cd "$(dirname "$0")"
./build.sh
version=$(sed -n 's/^Version: //p' krelboyneos-tools/DEBIAN/control)
deb="dist/krelboyneos-tools_${version}_all.deb"

rm -rf repo
mkdir -p repo/pool/main/k/krelboyneos-tools repo/dists/stable/main/binary-amd64
cp "$deb" repo/pool/main/k/krelboyneos-tools/

cd repo
# No Packages.gz: Cloudflare caches .gz files for hours, so after a publish apt
# got the new InRelease with the old Packages.gz and refused the mismatch.
# Files without an extension (Packages, InRelease) are never cached.
apt-ftparchive packages pool > dists/stable/main/binary-amd64/Packages
apt-ftparchive \
	-o APT::FTPArchive::Release::Origin=KrelboyneOS \
	-o APT::FTPArchive::Release::Label=KrelboyneOS \
	-o APT::FTPArchive::Release::Suite=stable \
	-o APT::FTPArchive::Release::Codename=stable \
	-o APT::FTPArchive::Release::Architectures=amd64 \
	-o APT::FTPArchive::Release::Components=main \
	-o APT::FTPArchive::Release::Description="KrelboyneOS tools" \
	release dists/stable > Release.new   # outside dists/stable, or it lists itself
mv Release.new dists/stable/Release

# Sign: InRelease (signed inline) and Release.gpg (separate signature)
gpg --default-key "$KEY" --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --default-key "$KEY" --armor --detach-sign -o dists/stable/Release.gpg dists/stable/Release
gpg --verify dists/stable/InRelease 2>&1 | grep -E 'Good signature|BAD' || true
cd ..

if [ "$1" = "--no-upload" ]; then
	echo "Signed repository in packages/repo (not uploaded)."
	exit 0
fi

rclone sync --s3-no-check-bucket repo "$REMOTE"
echo "Published krelboyneos-tools $version to $REMOTE"

# Check what apt will actually download: every file the Release lists, through dl.krelboyneos.org
url=https://dl.krelboyneos.org/apt/dists/stable
curl -fsS "$url/InRelease" | cmp -s - repo/dists/stable/InRelease || { echo "dl.krelboyneos.org serves an old InRelease." >&2; exit 1; }
awk '/^SHA256:/ {s=1; next} /^[^ ]/ {s=0} s {print $1, $3}' repo/dists/stable/Release | while read -r sum file; do
	got=$(curl -fsS "$url/$file" | sha256sum | cut -d' ' -f1)
	[ "$got" = "$sum" ] || { echo "dl.krelboyneos.org serves an old $file (a cached copy?)." >&2; exit 1; }
done
echo "dl.krelboyneos.org serves the new repository."
