"""Publish exactly the reviewed stable Windows trio using the official gh CLI.

Run --check-version before building; run without arguments after tests/build.
Drafts may be resumed, but conflicting assets and published releases are never
modified. GH_TOKEN is inherited by gh and is never included in diagnostics.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STABLE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
SHA = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?")


class PublishError(RuntimeError):
    pass


class ApiError(PublishError):
    def __init__(self, status=None):
        self.status = status
        super().__init__(f"GitHub API request failed (HTTP {status or 'unknown'}).")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise PublishError("Local checkout or release tag could not be verified.")
    return result.stdout.strip()


def preflight(root, env):
    repo, tag, source_sha = (env.get(k, "") for k in ("GITHUB_REPOSITORY", "GITHUB_REF_NAME", "GITHUB_SHA"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise PublishError("GITHUB_REPOSITORY must identify the current owner/repository.")
    if not tag.startswith("v") or not STABLE.fullmatch(tag[1:]):
        raise PublishError("Only stable tags vX.Y.Z may publish a release; test tags are not releases.")
    if not SHA.fullmatch(source_sha):
        raise PublishError("GITHUB_SHA must be a complete commit or annotated-tag SHA.")
    source = (root / "lolhex/__init__.py").read_text(encoding="utf-8")
    if git(root, "show", "HEAD:lolhex/__init__.py") != source.strip():
        raise PublishError("Source version file differs from the checked-out commit.")
    tree = ast.parse(source)
    versions = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
    if versions != [tag[1:]] or (root / "lolhex/_build.py").exists():
        raise PublishError("Stable tag must exactly match the checked-out source version, without test build metadata.")
    head = git(root, "rev-parse", "--verify", "HEAD^{commit}").lower()
    event_commit = git(root, "rev-parse", "--verify", source_sha + "^{commit}").lower()
    tag_commit = git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}").lower()
    if head != event_commit or head != tag_commit:
        raise PublishError("Checked-out HEAD, event SHA and release tag must resolve to the same commit.")
    return repo, tag, head


def artifacts(root, version):
    directory = root / "build/release"
    names = [f"DDHEX-Setup-{version}.exe", f"DDHEX-Portable-{version}.zip", "SHA256SUMS.txt"]
    result = {}
    for name in names:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
            raise PublishError(f"Missing or empty release artifact: {name}")
        result[name] = {"path": path, "size": path.stat().st_size, "sha256": digest(path)}
    sums = {}
    for line in result["SHA256SUMS.txt"]["path"].read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})[ \t]+\*?([^/\\]+)", line)
        if not match or match[2] in sums:
            raise PublishError("SHA256SUMS.txt contains an invalid or duplicate entry.")
        sums[match[2]] = match[1].lower()
    if set(sums) != set(names[:2]) or any(sums[name] != result[name]["sha256"] for name in names[:2]):
        raise PublishError("SHA256SUMS.txt must exactly match the installer and portable ZIP.")
    return result


class GitHub:
    def __init__(self, root, env):
        self.root = root
        self.env = dict(env, GH_HOST="github.com", GH_PROMPT_DISABLED="1", GH_DEBUG="")

    def run(self, *args):
        try:
            result = subprocess.run(["gh", *args], cwd=self.root, env=self.env,
                                    capture_output=True, check=False)
        except OSError:
            raise PublishError("The official gh CLI is required.") from None
        if result.returncode:
            # Never print stderr/stdout: gh diagnostics may contain credentials.
            raise PublishError("GitHub CLI operation failed; any existing draft was retained.")
        return result.stdout

    def api(self, endpoint):
        try:
            result = subprocess.run(["gh", "api", endpoint, "--hostname", "github.com", "--include"],
                                    cwd=self.root, env=self.env, capture_output=True, check=False)
        except OSError:
            raise PublishError("The official gh CLI is required.") from None
        response = result.stdout.replace(b"\r\n", b"\n")
        status = re.match(rb"HTTP/\S+\s+(\d+)", response)
        code = int(status[1]) if status else None
        if result.returncode or code is None or code >= 400:
            raise ApiError(code)
        try:
            return json.loads(response.split(b"\n\n", 1)[1])
        except (ValueError, IndexError):
            raise PublishError("GitHub API returned an invalid JSON response.") from None

    def asset_digest(self, repo, asset_id):
        if type(asset_id) is not int or asset_id <= 0:
            raise PublishError("Release asset has no valid GitHub asset ID.")
        # Older GitHub responses have no digest; verify the downloaded bytes instead.
        with tempfile.TemporaryFile() as errors:
            try:
                process = subprocess.Popen(["gh", "api", f"repos/{repo}/releases/assets/{asset_id}",
                                            "--hostname", "github.com", "--header", "Accept: application/octet-stream"],
                                           cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=errors)
            except OSError:
                raise PublishError("The official gh CLI is required.") from None
            value, size = hashlib.sha256(), 0
            with process.stdout:
                for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
                    value.update(chunk)
                    size += len(chunk)
            if process.wait():
                raise PublishError("Could not verify release asset bytes; release was not published.")
            return size, value.hexdigest()


def remote_tag_commit(gh, repo, tag):
    ref = gh.api(f"repos/{repo}/git/ref/tags/{tag}")
    if ref.get("ref") != f"refs/tags/{tag}":
        raise PublishError("Remote tag reference did not match the requested release.")
    obj, seen = ref.get("object") or {}, set()
    for _ in range(8):
        kind, sha = obj.get("type"), obj.get("sha", "")
        if not SHA.fullmatch(sha) or sha in seen:
            break
        if kind == "commit":
            return sha.lower()
        if kind != "tag":
            break
        seen.add(sha)
        obj = gh.api(f"repos/{repo}/git/tags/{sha}").get("object") or {}
    raise PublishError("Remote annotated tag did not resolve to a valid commit.")


def release_for(gh, repo, tag):
    known = None
    try:
        known = gh.api(f"repos/{repo}/releases/tags/{tag}")
        if not isinstance(known, dict):
            raise PublishError("Release metadata is not an object.")
        if known.get("draft") is False:
            return known
    except ApiError as exc:
        if exc.status != 404:
            raise
    # GitHub can hide drafts from the by-tag endpoint. Authenticated release
    # listing includes them; scan every page before concluding creation is safe.
    matches, page = [], 1
    while True:
        rows = gh.api(f"repos/{repo}/releases?per_page=100&page={page}")
        if not isinstance(rows, list):
            raise PublishError("Release listing could not be verified; no draft was created.")
        matches.extend(row for row in rows if isinstance(row, dict) and row.get("tag_name") == tag)
        if len(rows) < 100:
            break
        page += 1
    if known is not None and not any(row.get("id") == known.get("id") for row in matches):
        matches.append(known)
    if len(matches) > 1:
        raise PublishError("Multiple releases match this tag; no draft was created or modified.")
    return matches[0] if matches else None


def verify_release(gh, repo, tag, commit, release, local, *, complete):
    if not isinstance(release, dict):
        raise PublishError("Release metadata is not an object.")
    if (release.get("tag_name") != tag or release.get("prerelease") is not False
            or type(release.get("draft")) is not bool or type(release.get("id")) is not int):
        raise PublishError("Existing release version/type does not match this stable release.")
    target = release.get("target_commitish") or ""
    if not isinstance(target, str):
        raise PublishError("Release target metadata is invalid.")
    # The verified remote tag is authoritative. GitHub often stores a branch
    # name here; that branch may move after publication without changing a tag.
    # A literal SHA, however, must agree with our explicitly pinned target.
    if not target or (SHA.fullmatch(target) and target.lower() != commit):
        raise PublishError("Existing release target does not match the checked-out source commit.")
    remote = {}
    for asset in release.get("assets") or []:
        name = asset.get("name")
        if name not in local or name in remote:
            raise PublishError("Existing release contains unexpected or duplicate assets; no assets were replaced.")
        expected = local[name]
        if asset.get("state") != "uploaded" or type(asset.get("size")) is not int or asset["size"] != expected["size"]:
            raise PublishError(f"Existing release asset size/state conflicts: {name}")
        claimed = asset.get("digest")
        if claimed is None or claimed == "":
            size, sha = gh.asset_digest(repo, asset.get("id"))
        else:
            if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", str(claimed)):
                raise PublishError(f"Existing release asset has an unsupported digest: {name}")
            size, sha = asset["size"], claimed[7:].lower()
        if size != expected["size"] or sha != expected["sha256"]:
            raise PublishError(f"Existing release asset hash conflicts: {name}")
        remote[name] = asset
    if complete and set(remote) != set(local):
        raise PublishError("Release is missing required assets; it was not published or changed.")
    return set(local) - set(remote)


def publish(root, env, gh=None):
    repo, tag, commit = preflight(root, env)
    local = artifacts(root, tag[1:])
    if not env.get("GH_TOKEN"):
        raise PublishError("GH_TOKEN is required for release publishing.")
    gh = gh or GitHub(root, env)
    if remote_tag_commit(gh, repo, tag) != commit:
        raise PublishError("Remote tag points to another commit; nothing was published.")
    release = release_for(gh, repo, tag)
    if release is None:
        gh.run("release", "create", tag, "--repo", repo, "--draft", "--verify-tag", "--target", commit,
               "--title", f"DD HEX {tag[1:]}", "--notes", f"DD HEX {tag[1:]} Windows 10/11 x64。安装版、便携版及 SHA-256 校验和。")
        release = release_for(gh, repo, tag)
        if release is None:
            raise PublishError("Created draft could not be verified; no assets were published.")
    missing = verify_release(gh, repo, tag, commit, release, local, complete=not release["draft"])
    if not release["draft"]:
        return "already published"
    release_id = release["id"]
    if missing:
        gh.run("release", "upload", tag, *[str(local[name]["path"]) for name in sorted(missing)], "--repo", repo)
    release = release_for(gh, repo, tag)
    if release is None or release.get("id") != release_id:
        raise PublishError("Release identity changed during upload; no publishing was attempted.")
    verify_release(gh, repo, tag, commit, release, local, complete=True)
    if not release["draft"]:
        return "already published"
    if remote_tag_commit(gh, repo, tag) != commit:
        raise PublishError("Remote tag changed during upload; draft was retained.")
    gh.run("release", "edit", tag, "--repo", repo, "--draft=false", "--verify-tag")
    final = release_for(gh, repo, tag)
    if final is None or final.get("id") != release_id or final.get("draft") is not False:
        raise PublishError("Release publication could not be confirmed.")
    verify_release(gh, repo, tag, commit, final, local, complete=True)
    return "published"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-version", action="store_true", help="local stable tag/source validation only")
    args = parser.parse_args(argv)
    try:
        if args.check_version:
            _, tag, _ = preflight(ROOT, os.environ)
            print(f"Stable source/tag verified: {tag}")
        else:
            result = publish(ROOT, os.environ)
            print(f"Release {result}: https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases/tag/{os.environ['GITHUB_REF_NAME']}")
        return 0
    except (PublishError, OSError, ValueError, SyntaxError, TypeError, KeyError):
        # Exception text from filesystem/JSON/git/gh can contain external inputs.
        # Keep failures actionable using only our own controlled diagnostics.
        exc = sys.exception()
        print(str(exc) if isinstance(exc, PublishError) else "Release inputs could not be validated; nothing was overwritten.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
