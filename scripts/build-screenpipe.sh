#!/bin/bash
# Personal, non-commercial build of screenpipe (no paid app).
set -euo pipefail
SUPPORT="$HOME/Library/Application Support/Timeless"
SRC="$SUPPORT/src/screenpipe"
mkdir -p "$SUPPORT/src"
if [ ! -d "$SRC/.git" ]; then
  git clone --depth 1 https://github.com/screenpipe/screenpipe.git "$SRC"
fi
export PATH="/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
cd "$SRC"
echo "Building screenpipe from $SRC — this can take a long time."
if [ -f Cargo.toml ]; then
  cargo build --release -p screenpipe-engine
else
  echo "Unexpected screenpipe layout; see $SRC/README.md"
  ls
fi
