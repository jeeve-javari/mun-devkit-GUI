#!/usr/bin/env bash
# Copyright 2026 Iván Moreno Mendoza
# SPDX-License-Identifier: Apache-2.0
# Assemble build/frt-boot + build/content/{game.pck,frt} for mdk pack/sim.
#
# Usage (from a game project that has mun-project.toml):
#   /path/to/mun-devkit/engines/godot3/tools/assemble-layout.sh \
#       --pck /path/to/TailsFromAlteria.pck \
#       --frt /path/to/frt_aarch64_3.5.2 \
#       --out build
set -eu

pck=""
frt=""
out="build"
boot=""

while [ $# -gt 0 ]; do
  case "$1" in
    --pck) pck=$2; shift 2 ;;
    --frt) frt=$2; shift 2 ;;
    --out) out=$2; shift 2 ;;
    --boot) boot=$2; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$pck" ] || [ ! -f "$pck" ]; then
  echo "need --pck path/to/game.pck" >&2
  exit 2
fi
if [ -z "$frt" ] || [ ! -f "$frt" ]; then
  echo "need --frt path/to/aarch64-frt-binary" >&2
  exit 2
fi

root=$(cd "$(dirname "$0")/../../.." && pwd)
if [ -z "$boot" ]; then
  boot="$root/engines/godot3/frt-boot/frt-boot"
fi
if [ ! -f "$boot" ]; then
  echo "building frt-boot..."
  make -C "$root/engines/godot3/frt-boot" OUT="$root/engines/godot3/frt-boot/frt-boot"
  boot="$root/engines/godot3/frt-boot/frt-boot"
fi

mkdir -p "$out/content"
cp -f "$boot" "$out/frt-boot"
chmod +x "$out/frt-boot"
cp -f "$pck" "$out/content/game.pck"
cp -f "$frt" "$out/content/frt"
chmod +x "$out/content/frt"

echo "Assembled:"
echo "  $out/frt-boot          (card entry)"
echo "  $out/content/game.pck"
echo "  $out/content/frt"
echo "Next: mdk pack / mdk sim --container  (from the project that owns mun-project.toml)"
