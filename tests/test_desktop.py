import sys

from social_sanitizer import desktop


def test_output_goes_to_log_when_there_is_no_console(monkeypatch, tmp_path):
    """pythonw.exe on Windows starts apps with sys.stdout/sys.stderr set to None."""
    log = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(desktop, "log_file", lambda: log)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    desktop.ensure_output_streams()
    try:
        print("hello from a windowless app")
        sys.stderr.write("progress bar\n")
    finally:
        sys.stdout.close()

    assert log.read_text(encoding="utf-8") == "hello from a windowless app\nprogress bar\n"


def test_existing_console_is_left_alone(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "log_file", lambda: tmp_path / "app.log")
    before = (sys.stdout, sys.stderr)
    desktop.ensure_output_streams()
    assert (sys.stdout, sys.stderr) == before
    assert not (tmp_path / "app.log").exists()


def test_icon_is_packaged():
    assert desktop.icon_path().is_file()
