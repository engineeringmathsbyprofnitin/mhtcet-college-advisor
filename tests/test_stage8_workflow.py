"""Stage 8: checks the combined workflow is valid and safe (needs PyYAML; skipped if missing)."""
import os, re, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
try: import yaml
except ImportError: yaml = None

@unittest.skipIf(yaml is None, "PyYAML not installed")
class T(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, ".github", "workflows", "discover-sources.yml"), encoding="utf-8") as f: self.text = f.read()
        self.w = yaml.safe_load(self.text); self.steps = {s.get("name", s.get("uses", "")): s for s in self.w["jobs"]["discover"]["steps"]}
        self.names = list(self.steps)
    def idx(self, prefix): return [i for i, n in enumerate(self.names) if n.startswith(prefix)][0]
    def test_steps_run_in_the_right_order(self):
        self.assertLess(self.idx("Self-tests"), self.idx("Discover sources")); self.assertLess(self.idx("Discover sources"), self.idx("Download the documents")); self.assertLess(self.idx("Download the documents"), self.idx("Store new original")); self.assertLess(self.idx("Store new original"), self.idx("Save the reports"))
    def test_selftests_include_the_stage8_tests(self):
        run = self.steps[self.names[self.idx("Self-tests")]]["run"]; self.assertIn("test_stage8_download.py", run); self.assertIn("test_stage8_policy.py", run)
    def test_download_step_has_summary_and_optional_force_but_no_injection_risk(self):
        s = self.steps[self.names[self.idx("Download the documents")]]; self.assertIn("--github-summary", s["run"]); self.assertIn("$FORCE_FLAG", s["run"]); self.assertNotIn("${{", s["run"])
        self.assertEqual(self.w[True]["workflow_dispatch"]["inputs"]["force_download"]["type"], "boolean")
    def test_only_the_built_in_token_is_used(self):
        self.assertEqual(sorted(set(re.findall(r"secrets\.([A-Za-z_]+)", self.text))), ["GITHUB_TOKEN"]); self.assertNotIn("pull_request_target", self.text)
    def test_storing_and_saving_run_even_if_an_earlier_step_failed(self):
        for p in ("Store new original", "Save the reports", "Keep a copy"): self.assertEqual(self.steps[self.names[self.idx(p)]].get("if"), "always()")
    def test_storing_skips_files_already_in_the_release_and_confirms_only_what_was_stored(self):
        run = self.steps[self.names[self.idx("Store new original")]]["run"]
        self.assertIn("grep -qxF", run); self.assertIn("gh release upload", run); self.assertIn("ingestion.archive confirm", run); self.assertIn("-s uploaded.txt", run); self.assertNotIn("--clobber", run)     # never overwrites an original file
    def test_original_files_are_never_committed_to_git(self):
        save = self.steps[self.names[self.idx("Save the reports")]]["run"]; adds = " ".join(l for l in save.splitlines() if "git add" in l)
        self.assertNotIn("files", adds); self.assertIn("data/raw/manifest.json", adds)
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f: self.assertIn("data/raw/files/", f.read())
    def test_commit_step_copes_with_other_commits(self): self.assertIn("git pull --rebase", self.steps[self.names[self.idx("Save the reports")]]["run"])
if __name__ == "__main__": unittest.main()
