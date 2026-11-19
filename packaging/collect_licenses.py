"""Copy installed-wheel notices without importing packages or accessing the network.

Run this with the exact interpreter used for the Windows build. Existing files
are retained; platform manifests distinguish checked-in examples from the
current build environment. This is an inventory, not a compliance certificate.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import platform
from pathlib import Path, PurePosixPath
import re
import sys


NOTICE_NAME = re.compile(r"licen[sc]e|copying|notice|copyright", re.IGNORECASE)
TEXT_SUFFIXES = {"", ".txt", ".md", ".rst", ".apache", ".bsd", ".gpl", ".lgpl"}
EXTRA_PACKAGES = {"pyside6-essentials": "PySide6", "shiboken6": "shiboken6", "onnxruntime": "onnxruntime",
                  "opencv-python": "cv2", "rapidocr": "rapidocr"}


def safe_relative(value: str) -> PurePosixPath:
    value = str(value).replace("\\", "/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ":" in value or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError(f"Unsafe license path: {value!r}")
    return path


def contained_path(root: Path, relative: str) -> Path:
    path = root.joinpath(*safe_relative(relative).parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"License path escapes inventory root: {relative!r}")
    return path


def is_notice(path: Path) -> bool:
    # Include nested LICENSE-antlr4 and dragon4_LICENSE files as well as notices
    # with standard text suffixes. Never pick native binaries or Python code.
    return bool(NOTICE_NAME.search(path.name)) and (path.suffix.lower() in TEXT_SUFFIXES or "." not in path.name)


def component(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+\-]*", value):
        raise ValueError(f"Unsafe package identity: {value!r}")
    return value


def collect(output: Path, *, distributions=None) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    installed = list(metadata.distributions() if distributions is None else distributions)
    for dist in sorted(installed, key=lambda d: d.metadata.get("Name", "").lower()):
        name = dist.metadata.get("Name") or "unknown"
        key = re.sub(r"[-_.]+", "-", component(name)).lower()
        version = component(str(dist.version))
        site = Path(dist.locate_file("")).resolve()
        records = [str(p).replace("\\", "/") for p in dist.files or []]
        candidates = {p for p in records if is_notice(Path(p))}
        info_dirs = {p.split("/")[0] for p in records if ".dist-info/" in p or ".egg-info/" in p}
        for declared in dist.metadata.get_all("License-File") or []:
            declared = str(safe_relative(declared))
            for directory in info_dirs:
                for relative in (f"{directory}/licenses/{declared}", f"{directory}/{declared}"):
                    if contained_path(site, relative).is_file():
                        candidates.add(relative)
        # Some wheels omit notices from their metadata's License-File field.
        # Inspect the known runtime package directory too, including Qt licenses.
        package = EXTRA_PACKAGES.get(key)
        if package:
            package_dir = contained_path(site, package)
            if package_dir.is_dir():
                for source in package_dir.rglob("*"):
                    if source.is_file() and is_notice(source):
                        candidates.add(source.relative_to(site).as_posix())
        files = []
        for relative in sorted(candidates):
            source = contained_path(site, relative)
            if not source.is_file():
                continue
            destination = f"{key}/{version}/{safe_relative(relative)}"
            target = contained_path(output, destination)
            target.parent.mkdir(parents=True, exist_ok=True)
            body = source.read_bytes()
            target.write_bytes(body)
            files.append({"installed_path": relative, "destination": destination,
                          "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        models, model_metadata = [], []
        if key == "rapidocr":
            for relative in ("rapidocr/config.yaml", "rapidocr/default_models.yaml"):
                source = contained_path(site, relative)
                if source.is_file():
                    destination = f"{key}/{version}/{relative}"
                    target = contained_path(output, destination)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    body = source.read_bytes()
                    target.write_bytes(body)
                    model_metadata.append({"destination": destination, "sha256": hashlib.sha256(body).hexdigest()})
            for relative in records:
                if relative.startswith("rapidocr/models/") and relative.endswith(".onnx"):
                    source = contained_path(site, relative)
                    if source.is_file():
                        models.append({"installed_path": relative, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                       "bytes": source.stat().st_size})
        entries.append({"name": name, "version": version, "license_expression": dist.metadata.get("License-Expression"),
                        "license_metadata": dist.metadata.get("License"),
                        "project_urls": dist.metadata.get_all("Project-URL") or [], "files": files,
                        "models": models, "model_metadata": model_metadata, "wheel_notices_found": bool(files)})
    # PyInstaller redistributes the Python runtime too; it has no wheel metadata.
    python_root = Path(sys.base_prefix)
    python_files = []
    for relative in ("LICENSE.txt", f"lib/python{sys.version_info.major}.{sys.version_info.minor}/LICENSE.txt"):
        source = contained_path(python_root, relative)
        if source.is_file():
            destination = f"python/{platform.python_version()}/{relative}"
            target = contained_path(output, destination)
            target.parent.mkdir(parents=True, exist_ok=True)
            body = source.read_bytes()
            target.write_bytes(body)
            python_files.append({"installed_path": relative, "destination": destination,
                                 "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
    entries.append({"name": "CPython", "version": platform.python_version(), "files": python_files,
                    "project_urls": ["Source, https://www.python.org/downloads/source/"],
                    "wheel_notices_found": bool(python_files)})
    manifest = {"schema_version": 1, "python": platform.python_version(), "platform": sys.platform,
                "machine": platform.machine(), "scope": "Installed build environment; may include build/test-only packages. Retained files may come from other platforms. See README.md and per-platform manifests.",
                "packages": entries}
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    for filename in ("manifest.json", f"manifest-{component(sys.platform)}-{component(platform.machine() or 'unknown')}.json"):
        contained_path(output, filename).write_text(text, encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "THIRD_PARTY_LICENSES")
    args = parser.parse_args(argv)
    manifest = collect(args.output)
    count = sum(len(entry["files"]) for entry in manifest["packages"])
    print(f"Collected {count} notice files from {len(manifest['packages'])} installed distributions ({manifest['platform']}/{manifest['machine']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
