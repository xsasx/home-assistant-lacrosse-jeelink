#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: ./replace-owner.sh GITHUB_USERNAME"
  exit 1
fi

username="$1"
grep -RIl 'xsasx' . --exclude-dir=.git | while read -r file; do
  sed -i "s/xsasx/${username}/g" "$file"
done

echo "Repository owner set to ${username}."
