import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "github_preflight", Path(__file__).parents[1] / "tools" / "github_preflight.py"
)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class GitHubPreflightTests(unittest.TestCase):
    def metadata(self, **changes):
        return dict(nameWithOwner=guard.REPOSITORY, isPrivate=False,
                    viewerPermission="WRITE", **changes)

    def test_rejects_default_branch_and_other_remote(self):
        with self.assertRaises(guard.CheckError):
            guard.validate_target("main", f"https://github.com/{guard.REPOSITORY}.git")
        with self.assertRaises(guard.CheckError):
            guard.validate_target(guard.BRANCH, "https://github.com/other/repo.git")

    def test_rejects_embedded_credentials_and_multiple_destinations(self):
        for remote in ("https://secret@github.com/" + guard.REPOSITORY + ".git",
                       "https://github.com/" + guard.REPOSITORY + ".git\nother"):
            with self.assertRaises(guard.CheckError):
                guard.validate_target(guard.BRANCH, remote)

    def test_public_requires_explicit_flag(self):
        with self.assertRaises(guard.CheckError):
            guard.validate_metadata(self.metadata(), False)
        guard.validate_metadata(self.metadata(), True)

    def test_rejects_unknown_visibility_and_read_only_access(self):
        for field, value in (("isPrivate", None), ("viewerPermission", "READ")):
            data = self.metadata()
            data[field] = value
            with self.assertRaises(guard.CheckError):
                guard.validate_metadata(data, True)

    def test_authentication_failure_does_not_echo_sensitive_output(self):
        failed = subprocess.CompletedProcess(["gh"], 1, "", "secret-token")
        with patch.object(guard.subprocess, "run", return_value=failed):
            with self.assertRaises(guard.CheckError) as error:
                guard.command(["gh", "auth", "status"])
        self.assertNotIn("secret-token", str(error.exception))

    def test_timeout_is_bounded_and_reported(self):
        with patch.object(guard.subprocess, "run",
                          side_effect=subprocess.TimeoutExpired(["gh"], 20)) as run:
            with self.assertRaises(guard.CheckError):
                guard.command(["gh", "repo", "view"])
        self.assertEqual(run.call_args.kwargs["timeout"], 20)


if __name__ == "__main__":
    unittest.main()
