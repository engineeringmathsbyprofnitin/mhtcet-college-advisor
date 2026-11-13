"""Stage 10c-3c: the publish workflow and the preview / go-public switch. Run: python -m unittest tests/test_stage10c3c.py -v"""
import os, re, shutil, subprocess, sys, unittest
try:
    import yaml                      # not installed on a bare machine; the publish workflow installs it
except ImportError:
    yaml = None
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE = shutil.which("node")
WF = os.path.join(ROOT, ".github", "workflows", "publish-website-data.yml")

@unittest.skipUnless(yaml, "PyYAML not installed (pip install pyyaml)")
class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.y = yaml.safe_load(open(WF, encoding="utf-8")); cls.steps = cls.y["jobs"]["publish"]["steps"]
        cls.runs = [s.get("run", "") for s in cls.steps]
    def idx(self, text): return next(i for i, r in enumerate(self.runs) if text in r)
    def test_triggers(self):
        on = self.y[True] if True in self.y else self.y["on"]          # PyYAML reads the key `on` as True
        self.assertIn("workflow_dispatch", on); self.assertEqual(on["workflow_run"]["workflows"], ["Read the archived documents", "Read institute information"])
        self.assertIn("conclusion == 'success'", self.y["jobs"]["publish"]["if"])
    def test_permissions_are_minimal(self): self.assertEqual(self.y["permissions"], {"contents": "write"})
    def test_order_tests_then_validate_then_build_then_package_then_replace_then_commit(self):
        order = [self.idx(x) for x in ("unittest discover", "ingestion.plan", "ingestion.validate_cutoffs", "ingestion.build_tables", "ingestion.package_real", "rm -rf frontend/data-real", "git commit")]
        self.assertEqual(order, sorted(order)); self.assertEqual(len(set(order)), len(order))
    def test_package_goes_to_a_temporary_folder_so_a_failure_keeps_old_files(self):
        self.assertIn("build/data-real", self.runs[self.idx("ingestion.package_real")]); self.assertIn("cp -r build/data-real frontend/data-real", self.runs[self.idx("rm -rf frontend/data-real")])
    def test_only_expected_paths_are_committed(self):
        add = self.runs[self.idx("git commit")]; self.assertIn("git add frontend/data-real data/normalized/tables", add)
        self.assertNotIn("git add .", add); self.assertNotIn("git add -A", add)
    def test_every_python_module_it_runs_exists(self):
        for r in self.runs:
            for m in re.findall(r"python -m ingestion\.(\w+)", r): self.assertTrue(os.path.exists(os.path.join(ROOT, "ingestion", m + ".py")), m)

@unittest.skipUnless(NODE, "node not installed")
class Switch(unittest.TestCase):
    def cfg(self, search):
        js = "const w={location:{search:%r}};new Function('window',require('fs').readFileSync('frontend/config.js','utf8'))(w);console.log(w.APP_CONFIG.DATA_BASE_URL+'|'+w.APP_CONFIG.PREVIEW)" % search
        return subprocess.run([NODE, "-e", js], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
    def test_normal_address_uses_public_data(self): self.assertEqual(self.cfg(""), "data/|false")
    def test_preview_address_uses_real_data(self):
        self.assertEqual(self.cfg("?preview=1"), "data-real/|true"); self.assertEqual(self.cfg("?x=2&preview=1"), "data-real/|true")
    def test_lookalikes_do_not_switch(self):
        for q in ("?preview=10", "?preview=0", "?notpreview=1"): self.assertEqual(self.cfg(q), "data/|false", q)
    def test_go_public_is_one_line(self):
        src = open(os.path.join(ROOT, "frontend", "config.js"), encoding="utf-8").read()
        self.assertEqual(len(re.findall(r'^var PUBLIC_DATA_FOLDER = "data/";', src, re.M)), 1)
if __name__ == "__main__": unittest.main()


@unittest.skipUnless(yaml, "PyYAML not installed (pip install pyyaml)")
class InstitutesWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.y = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "read-institutes.yml"), encoding="utf-8")); cls.steps = cls.y["jobs"]["read"]["steps"]; cls.runs = [s.get("run", "") for s in cls.steps]
    def test_name_matches_the_publish_trigger(self): self.assertEqual(self.y["name"], "Read institute information")
    def test_runs_by_hand_and_weekly_with_minimal_permissions(self):
        on = self.y[True] if True in self.y else self.y["on"]; self.assertIn("workflow_dispatch", on); self.assertIn("schedule", on); self.assertEqual(self.y["permissions"], {"contents": "write"})
    def test_tests_before_reading_before_saving_only_the_institutes_folder(self):
        i = [next(k for k, r in enumerate(self.runs) if x in r) for x in ("unittest tests/test_stage10d.py", "ingestion.institutes", "git commit")]
        self.assertEqual(i, sorted(i)); add = self.runs[i[2]]; self.assertIn("git add data/normalized/institutes", add); self.assertNotIn("git add .", add)
