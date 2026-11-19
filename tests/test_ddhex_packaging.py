"""Distribution boundaries for the independent fork (no Windows required)."""

from pathlib import Path
from email.message import Message
import importlib.util
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


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

    def test_workflow_does_not_publish_or_fetch_upstream_data(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("upload-artifact", workflow)
        for command in ("git push", "gh release create", "purge.jsdelivr", "scripts/update_data.py", "czgreat/aramhex"):
            self.assertNotIn(command, workflow)

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
