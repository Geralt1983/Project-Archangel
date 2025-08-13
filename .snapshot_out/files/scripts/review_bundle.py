#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
import hashlib
from pathlib import Path

def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def git_changed(root: Path, base: str):
    """Return tracked changed files vs base, plus untracked new files."""
    tracked = set()
    ns = run(["git", "diff", "--numstat", base, "HEAD"], cwd=root).stdout.strip().splitlines()
    for line in ns:
        parts = line.split("\t")
        if len(parts) >= 3:
            tracked.add(parts[2])

    # Include staged but uncommitted
    ns_cached = run(["git", "diff", "--numstat", "--cached"], cwd=root).stdout.strip().splitlines()
    for line in ns_cached:
        parts = line.split("\t")
        if len(parts) >= 3:
            tracked.add(parts[2])

    # Include untracked files
    others = run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root).stdout.strip().splitlines()
    for path in others:
        tracked.add(path)

    # Filter obvious junk
    tracked = {p for p in tracked if not p.startswith(".git/") and p}
    return sorted(tracked)

def copy_files(root: Path, dest: Path, files: list[str]):
    for rel in files:
        src = root / rel
        if not src.exists() or not src.is_file():
            # If deleted or binary, skip copy; it still appears in diff
            continue
        out = dest / "files" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(src.read_bytes())

def ensure_nonempty_diff(root: Path, base: str) -> str:
    diff = run(["git", "diff", "--unified=3", base, "HEAD"], cwd=root).stdout
    if not diff.strip():
        # Fallback to last commit range
        diff = run(["git", "diff", "--unified=3", "HEAD~1", "HEAD"], cwd=root, check=False).stdout
    return diff

def guess_version(root: Path):
    for vf in ("pyproject.toml", "package.json"):
        p = root / vf
        if p.exists():
            for line in p.read_text().splitlines():
                if "version" in line:
                    return line.strip()
    return "version: unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root).stdout.strip()
    shortsha = run(["git", "rev-parse", "--short", "HEAD"], cwd=root).stdout.strip()

    changed = git_changed(root, args.base)
    copy_files(root, out, changed)

    diff = ensure_nonempty_diff(root, args.base)
    (out / "diff.patch").write_text(diff)

    pytest_txt = ""
    snap_tmp = root / ".snapshot_tmp"
    pt = snap_tmp / "pytest.txt"
    if pt.exists():
        pytest_txt = pt.read_text()
        (out / "artifacts" / "pytest.txt").write_text(pytest_txt)

    status = {
        "branch": branch,
        "commit": shortsha,
        "base": args.base,
        "generated_at_epoch": int(time.time()),
        "changed_files_count": len(changed),
    }
    (out / "status.json").write_text(json.dumps(status, indent=2))

    review = [
        f"# Change Summary ({branch}@{shortsha})",
        "- Why: <fill in>",
        "- Risk: low | medium | high",
        f"- Version: {guess_version(root)}",
        "- Rollback: revert above commit or redeploy previous snapshot",
        "",
        "## Files Changed",
        *(f"- {p}" for p in changed[:200]),
        "",
        "## Tests",
        "```",
        (pytest_txt.strip() or "no tests run"),
        "```",
        "",
        "## Decision Trace",
        "- <key decision 1>",
        "- <key decision 2>",
    ]
    (out / "REVIEW.md").write_text("\n".join(review))

    # manifest.json with sha256
    manifest = []
    for p in sorted(out.rglob("*")):
        if p.is_file():
            rel = p.relative_to(out).as_posix()
            manifest.append({"path": rel, "size": p.stat().st_size, "sha256": sha256_path(p)})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()