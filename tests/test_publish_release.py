"""Offline release publication: stable-only, draft-first and resumable without clobber."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import shutil

import pytest

SPEC = importlib.util.spec_from_file_location("publish_release", Path(__file__).resolve().parents[1] / "packaging/publish-release.py")
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def command(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(publisher.time, "sleep", lambda seconds: None)


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "lolhex").mkdir()
    (tmp_path / "lolhex/__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    command(tmp_path, "init", "--quiet")
    command(tmp_path, "add", ".")
    command(tmp_path, "-c", "user.name=Release test", "-c", "user.email=test@example.invalid", "commit", "--quiet", "-m", "Keep release fixture deterministic")
    commit = command(tmp_path, "rev-parse", "HEAD")
    command(tmp_path, "tag", "v1.2.3")
    output = tmp_path / "build/release"
    output.mkdir(parents=True)
    for name in ("DDHEX-Setup-1.2.3.exe", "DDHEX-Portable-1.2.3.zip"):
        (output / name).write_bytes((name + "-artifact").encode())
    (output / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n"
        for name in ("DDHEX-Setup-1.2.3.exe", "DDHEX-Portable-1.2.3.zip")), encoding="ascii")
    env = {"GITHUB_REPOSITORY": "independent/ddhex", "GITHUB_REF_NAME": "v1.2.3", "GITHUB_SHA": commit, "GH_TOKEN": "DO-NOT-LOG-TEST-TOKEN"}
    return tmp_path, env


class FakeGitHub:
    def __init__(self, root, env, *, release=None, annotated=False):
        self.root, self.env = root, env
        self.release = deepcopy(release)
        self.calls, self.downloads = [], []
        self.annotated = annotated
        self.hide_drafts_by_tag = False
        self.list_first_full_page = False
        self.hide_list = False
        self.id_not_found_reads = 0
        self.stale_asset_reads = 0
        self.stale_published_reads = 0
        self.remote_commit = env["GITHUB_SHA"]
        self.corrupt_upload = False
        self.incomplete_upload = False
        self.fail_upload = False
        self.moves_tag_after_upload = False
        self.local = publisher.artifacts(root, "1.2.3")

    def api(self, endpoint):
        self.calls.append(("api", endpoint))
        prefix = f"repos/{self.env['GITHUB_REPOSITORY']}"
        if endpoint == prefix + "/git/ref/tags/v1.2.3":
            return {"ref": "refs/tags/v1.2.3", "object": {"type": "tag" if self.annotated else "commit", "sha": "a" * 40 if self.annotated else self.remote_commit}}
        if endpoint == prefix + "/git/tags/" + "a" * 40:
            return {"object": {"type": "commit", "sha": self.remote_commit}}
        if endpoint == prefix + "/releases/41":
            if self.id_not_found_reads:
                self.id_not_found_reads -= 1
                raise publisher.ApiError(404)
            found = deepcopy(self.release)
            if self.stale_asset_reads and found["assets"]:
                self.stale_asset_reads -= 1
                found["assets"] = []
            if self.stale_published_reads and not found["draft"]:
                self.stale_published_reads -= 1
                found["draft"] = True
            return found
        if endpoint == prefix + "/commits/main":
            return {"sha": self.remote_commit}
        if endpoint == prefix + "/releases/tags/v1.2.3":
            if self.release is None or (self.hide_drafts_by_tag and self.release["draft"]):
                raise publisher.ApiError(404)
            return deepcopy(self.release)
        if endpoint.startswith(prefix + "/releases?per_page=100&page="):
            page = int(endpoint.rsplit("=", 1)[1])
            if self.list_first_full_page and page == 1:
                return [{"tag_name": f"v0.0.{number}"} for number in range(100)]
            return [deepcopy(self.release)] if self.release is not None and not self.hide_list else []
        raise AssertionError("Unexpected endpoint: " + endpoint)

    def create_draft(self, repo, tag, commit):
        assert repo == self.env["GITHUB_REPOSITORY"] and commit == self.env["GITHUB_SHA"]
        self.calls.append(("create", (repo, tag, commit)))
        assert self.release is None
        self.release = self.metadata()
        return deepcopy(self.release)

    def publish_draft(self, repo, release_id):
        assert repo == self.env["GITHUB_REPOSITORY"] and release_id == self.release["id"]
        assert len(self.release["assets"]) == 3
        self.calls.append(("run", ("release", "edit", "--id", release_id)))
        self.release["draft"] = False
        return deepcopy(self.release)

    def draft_for(self, repo, tag):
        assert repo == self.env["GITHUB_REPOSITORY"] and tag == "v1.2.3"
        self.calls.append(("discover", tag))
        return deepcopy(self.release)

    def run(self, *args):
        self.calls.append(("run", args))
        assert "--clobber" not in args
        assert args[args.index("--repo") + 1] == self.env["GITHUB_REPOSITORY"]
        if args[:2] == ("release", "upload"):
            paths = args[3:args.index("--repo")]
            for index, path in enumerate(paths):
                if self.incomplete_upload and index:
                    break
                self.release["assets"].append(self.asset(Path(path).name))
                if self.corrupt_upload:
                    self.release["assets"][-1]["digest"] = "sha256:" + "0" * 64
                if self.fail_upload:
                    raise publisher.PublishError("simulated partial upload")
            if self.moves_tag_after_upload:
                self.remote_commit = "f" * 40
        elif args[:2] == ("release", "edit"):
            assert "--draft=false" in args and "--verify-tag" in args
            assert len(self.release["assets"]) == 3
            self.release["draft"] = False
        else:
            raise AssertionError(args)

    def metadata(self, *, draft=True):
        return {"id": 41, "tag_name": "v1.2.3", "target_commitish": self.env["GITHUB_SHA"], "draft": draft, "prerelease": False, "assets": []}

    def asset(self, name):
        artifact = self.local[name]
        return {"id": list(self.local).index(name) + 1, "name": name, "state": "uploaded", "size": artifact["size"], "digest": "sha256:" + artifact["sha256"]}

    def asset_digest(self, repo, asset_id):
        self.downloads.append(asset_id)
        row = self.local[list(self.local)[asset_id - 1]]
        return row["size"], row["sha256"]


def mutations(gh):
    return [("release", "create", *args) if action == "create" else args
            for action, args in gh.calls if action in ("run", "create")]


def test_local_preflight_uses_source_ast_and_peels_annotated_event(checkout, monkeypatch):
    root, env = checkout
    command(root, "tag", "-d", "v1.2.3")
    command(root, "-c", "user.name=Release test", "-c", "user.email=test@example.invalid", "tag", "-a", "v1.2.3", "-m", "Reviewed stable release")
    env["GITHUB_SHA"] = command(root, "rev-parse", "v1.2.3")
    shutil.rmtree(root / "build")
    monkeypatch.setattr(publisher, "ROOT", root)
    monkeypatch.setattr(publisher.os, "environ", {k: v for k, v in env.items() if k != "GH_TOKEN"})
    monkeypatch.setattr(publisher, "GitHub", lambda *a: pytest.fail("preflight must not invoke gh"))
    assert publisher.main(["--check-version"]) == 0


@pytest.mark.parametrize("tag", ["v1.2.3-test.1", "v1.2.3-rc.1", "v1.2.3+build", "1.2.3", "v01.2.3", "v1.2.4"])
def test_test_tags_or_version_mismatch_fail_before_any_release(checkout, tag):
    root, env = checkout
    env["GITHUB_REF_NAME"] = tag
    gh = FakeGitHub(root, env)
    with pytest.raises(publisher.PublishError):
        publisher.publish(root, env, gh)
    assert not gh.calls


@pytest.mark.parametrize("problem", ["empty", "wrong_hash", "duplicate", "missing_sum", "wrong_head", "test_metadata", "uncommitted_source"])
def test_input_conflicts_fail_before_network(checkout, problem):
    root, env = checkout
    gh = FakeGitHub(root, env)
    sums = root / "build/release/SHA256SUMS.txt"
    if problem == "empty":
        (root / "build/release/DDHEX-Setup-1.2.3.exe").write_bytes(b"")
    elif problem == "wrong_hash":
        (root / "build/release/DDHEX-Portable-1.2.3.zip").write_bytes(b"changed")
    elif problem == "duplicate":
        sums.write_text(sums.read_text() * 2)
    elif problem == "missing_sum":
        sums.write_text(sums.read_text().splitlines()[0] + "\n")
    elif problem == "wrong_head":
        env["GITHUB_SHA"] = "f" * 40
    elif problem == "test_metadata":
        (root / "lolhex/_build.py").write_text('TEST_TAG = "test.1"')
    else:
        (root / "lolhex/__init__.py").write_text('__version__ = "1.2.3"\n# uncommitted\n')
    with pytest.raises(publisher.PublishError):
        publisher.publish(root, env, gh)
    assert not gh.calls


@pytest.mark.parametrize("annotated", [False, True])
def test_draft_first_exact_trio_and_idempotent_publish(checkout, annotated):
    root, env = checkout
    gh = FakeGitHub(root, env, annotated=annotated)
    assert publisher.publish(root, env, gh) == "published"
    assert [args[1] for args in mutations(gh)] == ["create", "upload", "edit"]
    assert {row["name"] for row in gh.release["assets"]} == set(gh.local)
    gh.calls.clear()
    assert publisher.publish(root, env, gh) == "already published"
    assert mutations(gh) == []


def test_resume_matching_partial_draft_and_verify_legacy_asset_bytes(checkout):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.release = gh.metadata()
    name = next(iter(gh.local))
    gh.release["assets"] = [gh.asset(name)]
    gh.release["assets"][0].pop("digest")
    assert publisher.publish(root, env, gh) == "published"
    uploaded = next(args for args in mutations(gh) if args[1] == "upload")
    assert all(Path(value).name != name for value in uploaded[3:uploaded.index("--repo")])
    assert gh.downloads and all(args[1] != "create" for args in mutations(gh))


@pytest.mark.parametrize("draft", [False, True])
@pytest.mark.parametrize("conflict", ["target", "tag", "prerelease", "size", "digest", "extra", "duplicate", "incomplete"])
def test_never_overwrite_conflicting_release(checkout, draft, conflict):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.release = gh.metadata(draft=draft)
    gh.release["assets"] = [gh.asset(name) for name in gh.local]
    if conflict == "target":
        gh.release["target_commitish"] = "e" * 40
    elif conflict == "tag":
        gh.release["tag_name"] = "v2.0.0"
    elif conflict == "prerelease":
        gh.release["prerelease"] = True
    elif conflict == "size":
        gh.release["assets"][0]["size"] += 1
    elif conflict == "digest":
        gh.release["assets"][0]["digest"] = "sha256:" + "0" * 64
    elif conflict == "extra":
        gh.release["assets"].append({"name": "debug.zip"})
    elif conflict == "duplicate":
        gh.release["assets"].append(gh.release["assets"][0])
    else:
        gh.release["assets"][0]["state"] = "starter"
    with pytest.raises(publisher.PublishError):
        publisher.publish(root, env, gh)
    assert mutations(gh) == []


def test_published_missing_asset_fails_without_repairing_it(checkout):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.release = gh.metadata(draft=False)
    with pytest.raises(publisher.PublishError, match="missing"):
        publisher.publish(root, env, gh)
    assert mutations(gh) == []


@pytest.mark.parametrize("problem", ["corrupt_upload", "incomplete_upload", "moves_tag_after_upload", "fail_upload"])
def test_upload_failure_retains_draft_and_does_not_publish(checkout, problem):
    root, env = checkout
    gh = FakeGitHub(root, env)
    setattr(gh, problem, True)
    with pytest.raises(publisher.PublishError):
        publisher.publish(root, env, gh)
    assert gh.release["draft"] is True
    assert all(args[1] != "edit" for args in mutations(gh))
    if problem == "fail_upload":
        gh.fail_upload = False
        assert publisher.publish(root, env, gh) == "published"


def test_remote_tag_target_is_verified_before_creating_release(checkout):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.remote_commit = "e" * 40
    with pytest.raises(publisher.PublishError, match="Remote tag"):
        publisher.publish(root, env, gh)
    assert mutations(gh) == []


def test_cli_errors_never_echo_credentials(checkout, monkeypatch, capsys):
    root, env = checkout
    monkeypatch.setattr(publisher, "ROOT", root)
    monkeypatch.setattr(publisher.os, "environ", env)
    def failure(*a, **kw):
        return subprocess.CompletedProcess(a, 1, stdout=b"secret-response", stderr=env["GH_TOKEN"].encode())
    original = publisher.subprocess.run
    monkeypatch.setattr(publisher.subprocess, "run", lambda args, **kw: original(args, **kw) if args[0] == "git" else failure(args, **kw))
    assert publisher.main([]) == 1
    output = capsys.readouterr()
    assert env["GH_TOKEN"] not in output.err + output.out and "secret-response" not in output.err + output.out


@pytest.mark.parametrize("existing", [False, True])
def test_hidden_drafts_are_discovered_without_duplicate_creation(checkout, existing):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.hide_drafts_by_tag = True
    gh.list_first_full_page = True
    if existing:
        gh.release = gh.metadata()
        gh.release["assets"] = [gh.asset(next(iter(gh.local)))]
    assert publisher.publish(root, env, gh) == "published"
    assert sum(args[1] == "create" for args in mutations(gh)) == (0 if existing else 1)
    assert any("page=2" in endpoint for action, endpoint in gh.calls if action == "api")


def test_published_release_branch_movement_does_not_change_tag_identity(checkout):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.release = gh.metadata(draft=False)
    gh.release["target_commitish"] = "main"
    gh.release["assets"] = [gh.asset(name) for name in gh.local]
    assert publisher.publish(root, env, gh) == "already published"
    assert mutations(gh) == []
    assert not any("/commits/" in endpoint for action, endpoint in gh.calls if action == "api")



def test_duplicate_matching_drafts_are_rejected_before_upload(checkout):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.release = gh.metadata()
    original = gh.api
    def duplicate(endpoint):
        if "/releases?" in endpoint:
            return [gh.metadata(), dict(gh.metadata(), id=42)]
        return original(endpoint)
    gh.api = duplicate
    with pytest.raises(publisher.PublishError, match="Multiple releases"):
        publisher.publish(root, env, gh)
    assert mutations(gh) == []


@pytest.mark.parametrize("existing", [False, True])
def test_stale_listing_does_not_hide_created_or_resumed_draft(checkout, existing):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.hide_drafts_by_tag, gh.hide_list = True, True
    gh.id_not_found_reads = 1
    gh.stale_asset_reads, gh.stale_published_reads = 1, 1
    if existing:
        gh.release = gh.metadata()
    assert publisher.publish(root, env, gh) == "published"
    assert sum(args[1] == "create" for args in mutations(gh)) == (0 if existing else 1)
    assert any(endpoint.endswith("/releases/41") for action, endpoint in gh.calls if action == "api")


def test_numeric_id_visibility_retry_is_bounded(checkout):
    root, env = checkout
    gh = FakeGitHub(root, env)
    gh.hide_drafts_by_tag, gh.hide_list = True, True
    gh.id_not_found_reads = 20
    with pytest.raises(publisher.ApiError):
        publisher.publish(root, env, gh)
    assert sum(endpoint.endswith("/releases/41") for action, endpoint in gh.calls if action == "api") == 4
    assert [args[1] for args in mutations(gh)] == ["create"]


def test_production_draft_create_captures_id_and_pending_lookup_uses_graphql(checkout, monkeypatch):
    root, env = checkout
    gh = publisher.GitHub(root, env)
    calls = []
    def api(endpoint, *options):
        calls.append((endpoint, options))
        if endpoint == "graphql":
            return {"data": {"repository": {"release": {"databaseId": 41, "tagName": "v1.2.3"}}}}
        return {"id": 41}
    monkeypatch.setattr(gh, "api", api)
    assert gh.create_draft(env["GITHUB_REPOSITORY"], "v1.2.3", env["GITHUB_SHA"])["id"] == 41
    assert "POST" in calls[0][1] and "draft=true" in calls[0][1] and "tag_name=v1.2.3" in calls[0][1]
    assert gh.draft_for(env["GITHUB_REPOSITORY"], "v1.2.3")["id"] == 41
    assert calls[-2][0] == "graphql" and calls[-1][0] == "repos/independent/ddhex/releases/41"
    assert gh.publish_draft(env["GITHUB_REPOSITORY"], 41)["id"] == 41
    assert calls[-1] == ("repos/independent/ddhex/releases/41", ("--method", "PATCH", "--field", "draft=false"))
