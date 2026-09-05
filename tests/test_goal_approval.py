"""Offline security regression tests; only synthetic commands and home directories."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))
from goal_approval import write_approval, _approval_path
import approve_goal


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.project = root / "project"
        self.project.mkdir()
        self.marker = root / "verifier-ran"
        self.env = {**os.environ, "HOME": str(self.home), "TMPDIR": str(root)}
        self.env.pop("PYTHONPATH", None)
        self.home_patch = patch.dict(os.environ, {"HOME": str(self.home)})
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.raw = json.dumps({
            "verify_command": "printf verified > " + shlex.quote(str(self.marker)),
            "error_pattern": "(0)",
        }).encode()
        (self.project / ".loopgain-goal.json").write_bytes(self.raw)

    def run_hook(self, project=None):
        result = subprocess.run(
            [sys.executable, "-S", str(HOOKS / "loopgain_stop.py")],
            input=json.dumps({"cwd": str(project or self.project), "session_id": "audit-test"}),
            text=True, capture_output=True, env=self.env, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_repository_config_cannot_arm_itself(self):
        result = self.run_hook()
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.home / ".loopgain").exists())
        self.assertEqual(result.stdout, "")
        self.assertIn("not approved", result.stderr)

    def test_malformed_config_is_inert(self):
        (self.project / ".loopgain-goal.json").write_text("[]")
        self.run_hook()
        self.assertFalse(self.marker.exists())

    def test_malformed_approval_is_inert(self):
        write_approval(self.project, self.raw)
        _approval_path(self.project).write_text("not json")
        self.run_hook()
        self.assertFalse(self.marker.exists())

    def test_revoked_approval_is_inert(self):
        write_approval(self.project, self.raw)
        _approval_path(self.project).unlink()
        self.run_hook()
        self.assertFalse(self.marker.exists())

    def test_approved_config_runs_verifier(self):
        write_approval(self.project, self.raw)
        self.run_hook()
        self.assertEqual(self.marker.read_text(), "verified")

    def test_changed_config_denied(self):
        write_approval(self.project, self.raw)
        modified = json.loads(self.raw)
        modified["timeout_seconds"] = 200
        (self.project / ".loopgain-goal.json").write_text(json.dumps(modified))
        self.run_hook()
        self.assertFalse(self.marker.exists())

    def test_copied_project_has_no_approval(self):
        write_approval(self.project, self.raw)
        other = self.project.parent / "other"
        other.mkdir()
        (other / ".loopgain-goal.json").write_bytes(self.raw)
        self.run_hook(other)
        self.assertFalse(self.marker.exists())

    def test_symlink_project_uses_canonical_approval(self):
        write_approval(self.project, self.raw)
        alias = self.project.parent / "alias"
        alias.symlink_to(self.project, target_is_directory=True)
        self.run_hook(alias)
        self.assertTrue(self.marker.exists())

    def test_symlink_approval_is_rejected(self):
        write_approval(self.project, self.raw)
        approval = _approval_path(self.project)
        moved = self.project.parent / "copied-approval"
        approval.rename(moved)
        approval.symlink_to(moved)
        self.run_hook()
        self.assertFalse(self.marker.exists())

    def test_shared_approval_permissions_rejected(self):
        write_approval(self.project, self.raw)
        _approval_path(self.project).chmod(0o644)
        self.run_hook()
        self.assertFalse(self.marker.exists())

    def test_approval_cli_rejects_piped_confirmation(self):
        result = subprocess.run(
            [sys.executable, str(HOOKS / "approve_goal.py"), str(self.project)],
            input="APPROVE\n", text=True, capture_output=True, env=self.env, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / ".loopgain").exists())

    def test_interactive_review_creates_approval(self):
        with patch.object(sys, "argv", ["approve_goal.py", str(self.project)]), \
             patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdout, "isatty", return_value=True), \
             patch("builtins.input", return_value="APPROVE"):
            self.assertEqual(approve_goal.main(), 0)
        self.run_hook()
        self.assertTrue(self.marker.exists())

    def test_changed_during_review_not_approved(self):
        def change(_):
            (self.project / ".loopgain-goal.json").write_bytes(self.raw + b"\n")
            return "APPROVE"
        with patch.object(sys, "argv", ["approve_goal.py", str(self.project)]), \
             patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdout, "isatty", return_value=True), \
             patch("builtins.input", side_effect=change):
            self.assertEqual(approve_goal.main(), 1)
        self.run_hook()
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
