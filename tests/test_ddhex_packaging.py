"""Distribution boundaries for the independent fork (no Windows required)."""

from pathlib import Path
from email.message import Message
import importlib.util
import re
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    # BaseLoader preserves GitHub's `on` key and leaves YAML booleans explicit.
    return yaml.load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def condition(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


class TestDDHexPackaging(unittest.TestCase):
    def test_independent_installer_identity(self):
        installer = (ROOT / "packaging/LolHex.iss").read_text(encoding="utf-8")
        self.assertIn("AppId={{0763032E-8343-4ADC-8A9F-F1625DFA68B7}", installer)
        self.assertIn("AppName=DD HEX 海克斯助手", installer)
        self.assertIn(r"DefaultDirName={localappdata}\Programs\DD HEX", installer)
        self.assertNotIn("czgreat", installer)
        self.assertNotIn("AramHex", installer)

    def test_executable_and_legal_documents_are_distributed(self):
        spec = (ROOT / "packaging/lolhex.spec").read_text(encoding="utf-8")
        build = (ROOT / "packaging/build.ps1").read_text(encoding="utf-8")
        self.assertIn('name="DD HEX"', spec)
        for name in ("LICENSE", "NOTICE.md", "PRIVACY.md", "README.md", "DATA-LICENSE-CC-BY-NC-4.0.txt", "THIRD_PARTY_LICENSES", "docs/WINDOWS.md"):
            self.assertIn(name, build)
        self.assertIn("DDHEX-Portable-$version.zip", build)
        self.assertIn("DDHEX-Setup-$version.exe", build)
        self.assertLess(build.index("Qt GUI 自检失败"), build.index("Inno Setup 编译失败"))

    def test_release_workflow_routes_stable_tags_to_official_windows_build(self):
        release = workflow("release.yml")
        self.assertEqual(release["permissions"], {"contents": "read"})
        triggers = release["on"]
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(triggers["push"]["tags"], ["v[0-9]+.[0-9]+.[0-9]+"])
        self.assertNotIn("branches", triggers["push"])
        job = release["jobs"]["release-windows"]
        gate = condition(job.get("if"))
        self.assertIn("github.event_name == 'push'", gate)
        self.assertIn("github.ref_type == 'tag'", gate)
        self.assertNotIn("||", gate)
        self.assertEqual(job["permissions"], {"contents": "write"})
        self.assertEqual(job["uses"], "./.github/workflows/windows-package.yml")
        self.assertEqual(job["with"]["official"], "true")
        self.assertNotIn("steps", job)

    def test_manual_windows_build_is_nonofficial_and_read_only(self):
        release = workflow("release.yml")
        job = release["jobs"]["test-windows"]
        gate = condition(job.get("if"))
        self.assertIn("github.event_name == 'workflow_dispatch'", gate)
        dispatch = release["on"]["workflow_dispatch"] or {}
        if "portable_tag" in dispatch.get("inputs", {}):
            self.assertIn("inputs.portable_tag == ''", gate)
        self.assertNotIn("||", gate)
        self.assertEqual(job["permissions"], {"contents": "read"})
        self.assertEqual(job["uses"], "./.github/workflows/windows-package.yml")
        self.assertEqual(job["with"]["official"], "false")
        self.assertNotIn("steps", job)

    def test_existing_portable_validation_cannot_publish(self):
        release = workflow("release.yml")
        # The existing portable-validation route is present on main; branches
        # without that validation feature still share the build/publish policy.
        validation = release["jobs"].get("validate-portable")
        if validation is None:
            return
        gate = condition(validation.get("if"))
        self.assertIn("github.event_name == 'workflow_dispatch'", gate)
        self.assertIn("inputs.portable_tag != ''", gate)
        self.assertNotIn("||", gate)
        self.assertEqual(validation.get("permissions", release["permissions"]), {"contents": "read"})
        steps = validation.get("steps", [])
        commands = "\n".join(step.get("run", "") for step in steps)
        self.assertIn("gh release download", commands)
        self.assertIn("Get-FileHash", commands)
        for step in steps:
            self.assertNotIn("upload-artifact", step.get("uses", ""))
        for command in ("gh release create", "gh release upload", "publish-release.py", "git push"):
            self.assertNotIn(command, commands)

    def test_reusable_windows_build_declares_boolean_publication_input(self):
        shared = workflow("windows-package.yml")
        self.assertEqual(set(shared["on"]), {"workflow_call"})
        official = shared["on"]["workflow_call"]["inputs"]["official"]
        self.assertEqual(official["type"], "boolean")
        self.assertEqual(official.get("default", "false"), "false")
        # A reusable workflow may downgrade its caller's token, never elevate
        # it. Inherit release=write/test=read instead of requesting write here.
        self.assertNotIn("permissions", shared)
        windows = [job for job in shared["jobs"].values() if job.get("runs-on") == "windows-latest"]
        self.assertEqual(len(windows), 1)
        self.assertNotIn("permissions", windows[0])
        commands = "\n".join(step.get("run", "") for step in windows[0].get("steps", []))
        self.assertIn("requirements-build.txt", commands)
        self.assertIn("scripts/check_release_data.py", commands)
        self.assertIn("pytest", commands)
        self.assertIn("packaging/build.ps1", commands)
        self.assertIn("python -m venv .venv", commands)
        build_index = next(i for i, step in enumerate(windows[0]["steps"]) if "packaging/build.ps1" in step.get("run", ""))
        checks = [step for step in windows[0]["steps"][:build_index]
                  if "packaging/publish-release.py --check-version" in step.get("run", "")]
        self.assertEqual(len(checks), 1)
        self.assertIn("inputs.official", condition(checks[0].get("if")))

    def test_temporary_packages_are_uploaded_only_for_manual_nonofficial_runs(self):
        shared = workflow("windows-package.yml")
        uploads = [step for job in shared["jobs"].values() for step in job.get("steps", [])
                   if "upload-artifact" in step.get("uses", "")]
        self.assertEqual(len(uploads), 1)
        gate = condition(uploads[0].get("if"))
        self.assertIn("!inputs.official", gate)
        self.assertIn("github.event_name == 'workflow_dispatch'", gate)
        self.assertNotIn("||", gate)
        paths = {line.strip() for line in uploads[0]["with"]["path"].splitlines() if line.strip()}
        self.assertEqual(paths, {"build/release/DDHEX-Setup-*.exe", "build/release/DDHEX-Portable-*.zip",
                                 "build/release/SHA256SUMS.txt"})
        self.assertEqual(uploads[0]["with"]["retention-days"], "3")
        self.assertEqual(uploads[0]["with"]["if-no-files-found"], "error")

    def test_official_publisher_is_tag_only_without_parallel_release_uploads(self):
        shared = workflow("windows-package.yml")
        publishers = [(job, step) for job in shared["jobs"].values() for step in job.get("steps", [])
                      if "packaging/publish-release.py" in step.get("run", "")
                      and "--check-version" not in step["run"]]
        self.assertEqual(len(publishers), 1)
        job, publish = publishers[0]
        gate = condition(publish.get("if"))
        for term in ("inputs.official", "github.event_name == 'push'", "github.ref_type == 'tag'"):
            self.assertIn(term, gate)
        self.assertNotIn("!inputs.official", gate)
        self.assertNotIn("||", gate)
        self.assertNotIn("permissions", shared)
        self.assertNotIn("permissions", job)
        self.assertIn("GH_TOKEN", publish.get("env", {}))
        self.assertIn("github.token", publish["env"]["GH_TOKEN"])
        build_index = next(i for i, step in enumerate(job["steps"]) if "packaging/build.ps1" in step.get("run", ""))
        self.assertGreater(job["steps"].index(publish), build_index)
        for name in ("release.yml", "windows-package.yml"):
            config = workflow(name)
            if name == "release.yml":
                expected = {"release-windows", "test-windows"}
                if "validate-portable" in config["jobs"]:
                    expected.add("validate-portable")
                self.assertEqual(set(config["jobs"]), expected)
            else:
                self.assertEqual(len(config["jobs"]), 1)
            for candidate in config["jobs"].values():
                if name == "release.yml":
                    self.assertFalse(any("upload-artifact" in step.get("uses", "") for step in candidate.get("steps", [])))
                for step in candidate.get("steps", []):
                    for command in ("gh release create", "gh release upload", "git push", "purge.jsdelivr", "scripts/update_data.py", "czgreat/aramhex"):
                        self.assertNotIn(command, step.get("run", ""))

    def test_crash_launcher_is_local_and_independent(self):
        launcher = (ROOT / "packaging/launcher.py").read_text(encoding="utf-8")
        self.assertIn('"DDHEX_HOME"', launcher)
        self.assertNotIn("aramhex.com", launcher)
        self.assertNotIn("webbrowser.open", launcher)

    def test_license_collection_is_contained_and_preserves_existing_files(self):
        spec = importlib.util.spec_from_file_location("collect_licenses", ROOT / "packaging/collect_licenses.py")
        collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            site = base / "site"
            site.mkdir()
            (site / "demo.dist-info").mkdir()
            (site / "demo.dist-info/LICENSE").write_text("license text", encoding="utf-8")
            metadata = Message()
            metadata["Name"] = "demo"
            metadata["License-File"] = "LICENSE"

            class FakeDistribution:
                version = "1.0"
                files = [Path("demo.dist-info/LICENSE")]

                def locate_file(self, path):
                    return site / path

            dist = FakeDistribution()
            dist.metadata = metadata
            output = base / "licenses"
            output.mkdir()
            (output / "retained.txt").write_text("keep", encoding="utf-8")
            manifest = collector.collect(output, distributions=[dist])
            entry = manifest["packages"][0]
            copied = output / entry["files"][0]["destination"]
            self.assertEqual(copied.read_text(encoding="utf-8"), "license text")
            self.assertEqual((output / "retained.txt").read_text(encoding="utf-8"), "keep")
            self.assertEqual(len(entry["files"][0]["sha256"]), 64)
            dist.files = [Path("../LICENSE")]
            with self.assertRaises(ValueError):
                collector.collect(output, distributions=[dist])

    def test_license_collection_rejects_output_symlink_escape(self):
        spec = importlib.util.spec_from_file_location("collect_licenses", ROOT / "packaging/collect_licenses.py")
        collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            output = base / "out"
            outside = base / "outside"
            output.mkdir()
            outside.mkdir()
            try:
                (output / "escape").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is unavailable")
            with self.assertRaises(ValueError):
                collector.contained_path(output, "escape/LICENSE")


if __name__ == "__main__":
    unittest.main()
