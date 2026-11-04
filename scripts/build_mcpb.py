#!/usr/bin/env python3
"""
Build script to package Extra into an Anthropic Claude Desktop Extension bundle (.mcpb).
Generates dist/extra.mcpb conforming to @anthropic-ai/mcpb v0.4 specification.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path


def build_mcpb(output_dir: Path | None = None) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = output_dir or (repo_root / "dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    output_bundle = dist_dir / "extra.mcpb"

    files_to_pack = [
        ("manifest.json", repo_root / "manifest.json"),
        ("package.json", repo_root / "package.json"),
        ("README.md", repo_root / "README.md"),
        ("LICENSE", repo_root / "LICENSE"),
        ("bin/cli.js", repo_root / "bin" / "cli.js"),
    ]

    print(f"Building Claude Desktop Extension bundle (.mcpb)...")
    with zipfile.ZipFile(output_bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, src_path in files_to_pack:
            if src_path.exists():
                print(f"  + {arcname}")
                zf.write(src_path, arcname)
            else:
                print(f"  [WARN] Missing source file: {src_path}")

    print(f"[OK] Successfully built {output_bundle} ({output_bundle.stat().st_size} bytes)")

    # Also sync to extra.yantraos.com public directory if available
    web_download_dir = repo_root.parent / "extra.yantraos.com" / "public" / "download"
    if web_download_dir.parent.exists():
        web_download_dir.mkdir(parents=True, exist_ok=True)
        dest = web_download_dir / "extra.mcpb"
        shutil.copy2(output_bundle, dest)
        print(f"[OK] Synced to website distribution: {dest}")

    return output_bundle


if __name__ == "__main__":
    build_mcpb()
