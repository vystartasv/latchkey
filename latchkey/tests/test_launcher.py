"""Tests for Latchkey daemon-launcher helpers."""

import socket
import tempfile

from latchkey import launcher


def test_is_daemon_running_without_socket(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "SOCKET_PATH", str(tmp_path / "latchkey.sock"))

    assert launcher.is_daemon_running() is False


def test_is_daemon_running_with_dead_daemon(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="lk-", dir="/tmp") as directory:
        socket_path = f"{directory}/socket"
        dead_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        dead_socket.bind(socket_path)
        dead_socket.close()
        monkeypatch.setattr(launcher, "SOCKET_PATH", socket_path)

        assert launcher.is_daemon_running() is False
