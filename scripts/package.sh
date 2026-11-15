#!/usr/bin/env bash
# Build the Flow Launcher plugin archive and print its path.
# Usage: scripts/package.sh [out_dir]   (default: dist)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out_dir="${1:-$root/dist}"
version="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["Version"])' "$root/data/plugin.json")"
build_dir="$(mktemp -d)"
wheel_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir" "$wheel_dir"' EXIT

# Copy only source files git knows about (tracked or new but not ignored), so
# local leftovers such as plugin.log and __pycache__ stay out of the archive.
while IFS= read -r -d '' path; do
  [ -f "$root/$path" ] || continue
  dest="$build_dir/${path#src/}"
  mkdir -p "$(dirname "$dest")"
  cp "$root/$path" "$dest"
done < <(git -C "$root" ls-files -z --cached --others --exclude-standard -- src)
cp "$root/data/icon.png" "$root/data/cast.png" "$root/data/plugin.json" "$root/LICENSE" "$build_dir/"

# zeroconf only publishes compiled wheels; build its pure-python fallback and tag it as such.
zeroconf_req="$(grep -i '^zeroconf==' "$root/requirements.txt")"
SKIP_CYTHON=1 python3 -m pip wheel --no-deps --no-binary zeroconf "$zeroconf_req" \
  -w "$wheel_dir" --quiet --disable-pip-version-check
python3 -m wheel tags --remove --python-tag py3 --abi-tag none --platform-tag any "$wheel_dir"/zeroconf-*.whl >/dev/null

# Pure-python wheels only: the zip is built on Linux but runs on the user's Windows Python.
python3 -m pip install -r "$root/requirements.txt" \
  --target "$build_dir/plugin/site-packages" \
  --only-binary=:all: --platform any --python-version 3.11 --implementation py \
  --find-links "$wheel_dir" --no-compile --quiet --disable-pip-version-check

mkdir -p "$out_dir"
zip_path="$(cd "$out_dir" && pwd)/flow-cast-${version}.zip"
rm -f "$zip_path"
(cd "$build_dir" && zip -qr "$zip_path" .)
echo "$zip_path"
