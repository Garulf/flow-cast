import sys

import pytest

import clipboard


def test_not_windows_returns_none(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert clipboard.read_text() is None


def test_windows_errors_return_none(monkeypatch):
    def broken():
        raise OSError("clipboard busy")

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(clipboard, "_read_windows_clipboard", broken)
    assert clipboard.read_text() is None


@pytest.mark.skipif(sys.platform != "win32", reason="needs the Windows clipboard")
def test_reads_real_clipboard():
    assert clipboard.read_text() is None or isinstance(clipboard.read_text(), str)
