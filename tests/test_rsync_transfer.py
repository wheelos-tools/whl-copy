"""Contract tests for rsync transfer command construction."""

from whl_copy.storage.operations import _build_ssh_cmd, rsync_push


def test_build_ssh_cmd_without_key():
    assert _build_ssh_cmd(None) == "ssh"


def test_build_ssh_cmd_with_key_quotes_path():
    cmd = _build_ssh_cmd("~/.ssh/my key")
    assert cmd.startswith("ssh -i ")
    assert "'~/.ssh/my key'" in cmd


def test_rsync_push_builds_expected_command(monkeypatch):
    captured = {}

    def fake_run(cmd, check=True, **kwargs):
        captured["cmd"] = cmd
        captured["check"] = check

    monkeypatch.setattr("whl_copy.storage.operations.subprocess.run", fake_run)

    rsync_push(
        src="/tmp/src",
        dst="/remote/dst",
        host="10.10.10.5",
        user="tester",
        ssh_key="~/.ssh/id_rsa",
        filter_args=["--min-size=1m"],
        extra_args=["--delete"],
        resume=True,
    )

    cmd = captured["cmd"]
    assert cmd[:2] == ["rsync", "-avz"]
    # accept either --progress (older) or --update (current implementation)
    assert any(f in cmd for f in ("--progress", "--update"))
    assert "--partial" in cmd
    assert "--min-size=1m" in cmd
    assert any(token.startswith("-e=ssh -i") for token in cmd)
    assert cmd[-2:] == ["tester@10.10.10.5:/remote/dst", "--delete"]
    assert captured["check"] is True
