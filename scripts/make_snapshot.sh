#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPDIR="${HOME}/Desktop/archangel-deployments/snapshots"
TMP="${ROOT}/.snapshot_tmp"
OUT="${ROOT}/.snapshot_out"
BASE_REF="${BASE_REF:-origin/main}"

mkdir -p "$SNAPDIR" "$TMP"
rm -rf "$OUT"
mkdir -p "$OUT" "$OUT/artifacts"

# 1) Ensure we have a base to diff against
if ! git rev-parse --verify -q "$BASE_REF" >/dev/null; then
  echo "WARN: BASE_REF '$BASE_REF' not found. Falling back to HEAD~1"
  BASE_REF="HEAD~1"
fi

# 2) Run tests with PYTHONPATH so imports like 'app.*' work
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
if command -v pytest >/dev/null 2>&1; then
  # Quiet but capture failures; do not stop the script on test failure
  python3 -m pytest -q --maxfail=1 --disable-warnings | tee "${TMP}/pytest.txt" || true
else
  echo "pytest not found; skipping tests" | tee "${TMP}/pytest.txt"
fi

# 3) Build the bundle (this script fills files/, diff.patch, status.json, REVIEW.md)
python3 "$ROOT/scripts/review_bundle.py" --out "$OUT" --base "$BASE_REF"

# Guard: require files/
if [ ! -d "$OUT/files" ] || [ -z "$(find "$OUT/files" -type f -print -quit)" ]; then
  echo "ERROR: snapshot contains no files. Aborting. Check your base ref or pending changes."
  exit 2
fi

# 4) Zip the bundle
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
SHORTSHA="$(git rev-parse --short HEAD)"
STAMP="$(date -u +"%Y%m%d_%H%M%S")"
ZIP="snapshot_${STAMP}_${BRANCH}_${SHORTSHA}.zip"

( cd "$OUT" && zip -qr "${SNAPDIR}/${ZIP}" . )

# Keep last 20 snapshots
ls -1t "${SNAPDIR}"/snapshot_*.zip 2>/dev/null | awk 'NR>20' | xargs -r rm -f

echo "Snapshot ready to drag: ${SNAPDIR}/${ZIP}"