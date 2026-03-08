#!/usr/bin/env bash
# build-cap.sh — 組裝 www/ 給 Capacitor 使用
# Usage: bash scripts/build-cap.sh

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW="$ROOT/www"

echo "==> Cleaning www/"
rm -rf "$WWW"
mkdir -p "$WWW"

echo "==> Copying index.html"
cp "$ROOT/templates/index.html" "$WWW/index.html"

echo "==> Copying static/"
cp -r "$ROOT/static" "$WWW/static"

echo "==> Done! www/ is ready for 'npx cap sync'"
