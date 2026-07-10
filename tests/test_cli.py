"""Tests for the FHSS CLI (cli.py)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from cli import (
    ROOT,
    cmd_status,
    cmd_dev,
    cmd_commit,
    check_cmd,
    wait_for_health,
    container_running,
    run,
)


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestHelpers:
    def test_check_cmd_found(self):
        with patch("shutil.which", return_value="/usr/bin/docker"):
            assert check_cmd("docker") is True

    def test_check_cmd_not_found(self):
        with patch("shutil.which", return_value=None):
            assert check_cmd("nonexistent") is False

    @patch("subprocess.run")
    def test_run_success(self, mock_run):
        mock_run.return_value = FakeCompletedProcess(0, "output", "")
        ok, out, err = run("echo hello")
        assert ok is True
        assert out == "output"
        assert err == ""

    @patch("subprocess.run")
    def test_run_failure(self, mock_run):
        mock_run.return_value = FakeCompletedProcess(1, "", "error msg")
        ok, out, err = run("false")
        assert ok is False

    @patch("subprocess.run")
    def test_run_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 120)
        ok, out, err = run("sleep 999")
        assert ok is False
        assert err == "timeout"

    @patch("subprocess.run")
    def test_run_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        ok, out, err = run("nonexistent_cmd")
        assert ok is False
        assert err == "not found"

    @patch("subprocess.run")
    def test_run_with_list_command(self, mock_run):
        mock_run.return_value = FakeCompletedProcess(0, "ok", "")
        ok, out, _ = run(["echo", "hello"])
        assert ok is True
        assert out == "ok"

    @patch("cli.run")
    @patch("json.loads")
    def test_wait_for_health_success(self, mock_json_loads, mock_run):
        mock_run.return_value = (True, '{"status": "UP"}', "")
        mock_json_loads.return_value = {"status": "UP"}
        assert wait_for_health("http://localhost:8080/health", max_retries=2, interval=0) is True

    @patch("cli.run")
    def test_wait_for_health_failure(self, mock_run):
        mock_run.return_value = (False, "", "")
        assert wait_for_health("http://localhost:8080/health", max_retries=2, interval=0) is False

    @patch("cli.docker_ps")
    def test_container_running_true(self, mock_ps):
        mock_ps.return_value = "fhss-postgres Up 2 hours"
        assert container_running("fhss-postgres") is True

    @patch("cli.docker_ps")
    def test_container_running_false(self, mock_ps):
        mock_ps.return_value = "fhss-postgres Exited"
        assert container_running("fhss-postgres") is False

    @patch("cli.docker_ps")
    def test_container_running_not_found(self, mock_ps):
        mock_ps.return_value = "fhss-redis Up 1 hour"
        assert container_running("fhss-postgres") is False


class FakeArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestCmdStatus:
    @patch("cli.run")
    @patch("cli.check_cmd")
    @patch("cli.container_running")
    def test_status_all_healthy(self, mock_container, mock_check, mock_run):
        mock_run.side_effect = [
            (True, "", ""),  # git status
            (True, "main", ""),  # git branch
            (True, '{"status": "UP"}', ""),  # backend health
            (True, '{"status": "UP", "model_version": "2.0.0"}', ""),  # ml health
        ]
        mock_check.return_value = True
        mock_container.return_value = True

        args = FakeArgs()
        cmd_status(args)

    @patch("cli.run")
    @patch("cli.check_cmd")
    @patch("cli.container_running")
    def test_status_git_dirty(self, mock_container, mock_check, mock_run):
        mock_run.side_effect = [
            (True, " M cli.py\n?? newfile.py", ""),  # git status dirty
            (True, "feature-branch", ""),  # git branch
            (True, "", ""),  # curl backend (unused, covered by container check)
            (True, "", ""),  # curl ml (unused)
        ]
        mock_check.return_value = True
        mock_container.return_value = True
        args = FakeArgs()
        cmd_status(args)


class TestCmdDev:
    @patch("cli.run")
    @patch("cli.check_cmd")
    @patch("cli.wait_for_health")
    @patch("subprocess.Popen")
    def test_dev_basic_startup(self, mock_popen, mock_health, mock_check, mock_run):
        mock_check.return_value = True
        mock_run.return_value = (True, "", "")
        mock_health.return_value = True

        args = FakeArgs(
            skip_seed=True,
            skip_train=True,
            skip_frontend=True,
            ml_docker=False,
            strict=False,
        )
        assert cmd_dev(args) is True

    @patch("cli.run")
    @patch("cli.check_cmd")
    def test_dev_docker_not_found(self, mock_check, mock_run):
        mock_check.return_value = False
        args = FakeArgs(skip_seed=True, skip_train=True, skip_frontend=True, ml_docker=False, strict=False)
        assert cmd_dev(args) is False

    @patch("cli.run")
    @patch("cli.check_cmd")
    @patch("cli.wait_for_health")
    def test_dev_strict_mode_fails(self, mock_health, mock_check, mock_run):
        mock_check.return_value = True
        mock_run.return_value = (True, "", "")
        mock_health.return_value = False

        args = FakeArgs(skip_seed=True, skip_train=True, skip_frontend=True, ml_docker=False, strict=True)
        assert cmd_dev(args) is False

    @patch("cli.run")
    @patch("cli.check_cmd")
    @patch("cli.wait_for_health")
    def test_dev_strict_mode_allows_warnings(self, mock_health, mock_check, mock_run):
        mock_check.return_value = True
        mock_run.return_value = (True, "", "")
        mock_health.return_value = False

        args = FakeArgs(skip_seed=True, skip_train=True, skip_frontend=True, ml_docker=False, strict=False)
        assert cmd_dev(args) is True


class TestCmdCommit:
    @patch("cli.cmd_status")
    @patch("cli.run")
    @patch("builtins.input")
    def test_commit_no_changes(self, mock_input, mock_run, mock_status):
        mock_run.side_effect = [
            (True, "", ""),  # git status (clean)
        ]
        args = FakeArgs()
        assert cmd_commit(args) is True

    @patch("cli.cmd_status")
    @patch("cli.run")
    @patch("builtins.input")
    def test_commit_aborted_no_message(self, mock_input, mock_run, mock_status):
        mock_run.side_effect = [
            (True, " M cli.py", ""),  # git status dirty
            (True, "", ""),  # git add
            (True, "1 file changed", ""),  # diff stat
        ]
        mock_input.side_effect = ["scoring", "feat", ""]  # scope, type, empty message
        args = FakeArgs()
        assert cmd_commit(args) is False

    @patch("cli.cmd_status")
    @patch("cli.run")
    @patch("builtins.input")
    def test_commit_success(self, mock_input, mock_run, mock_status):
        mock_run.side_effect = [
            (True, " M cli.py", ""),  # git status dirty
            (True, "", ""),  # git add
            (True, "1 file changed", ""),  # diff stat
            (True, "", ""),  # git commit
        ]
        mock_input.side_effect = ["scoring", "feat", "add scoring tests", "y"]
        args = FakeArgs()
        assert cmd_commit(args) is True

    @patch("cli.cmd_status")
    @patch("cli.run")
    @patch("builtins.input")
    def test_commit_user_aborts(self, mock_input, mock_run, mock_status):
        mock_run.side_effect = [
            (True, " M cli.py", ""),  # git status dirty
            (True, "", ""),  # git add
            (True, "1 file changed", ""),  # diff stat
        ]
        mock_input.side_effect = ["scoring", "feat", "add scoring tests", "n"]
        args = FakeArgs()
        assert cmd_commit(args) is True

    @patch("cli.cmd_status")
    @patch("cli.run")
    @patch("builtins.input")
    def test_commit_fails(self, mock_input, mock_run, mock_status):
        mock_run.side_effect = [
            (True, " M cli.py", ""),  # git status dirty
            (True, "", ""),  # git add
            (True, "1 file changed", ""),  # diff stat
            (False, "", "commit error"),  # git commit fails
        ]
        mock_input.side_effect = ["scoring", "feat", "add scoring tests", "y"]
        args = FakeArgs()
        assert cmd_commit(args) is False
