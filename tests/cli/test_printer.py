from os import linesep

import pytest

from neuromation.cli.printer import CSI, StreamPrinter, TTYPrinter


class TestStreamPrinter:
    @pytest.fixture
    def printer(self):
        return StreamPrinter()

    def test_no_messages(self, printer, capfd):
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == ""

    def test_one_message(self, printer, capfd):
        printer.print("message")
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f"message{linesep}"

    def test_two_messages(self, printer, capfd):
        printer.print("message1")
        printer.print("message2")
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f"message1{linesep}message2{linesep}"

    def test_ticks_without_messages(self, printer, capfd):
        printer.tick()
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f".{linesep}"

    def test_ticks_with_messages(self, printer, capfd, monkeypatch):
        monkeypatch.setattr("neuromation.cli.printer.TICK_TIMEOUT", 0)
        printer.tick()
        printer.print("message")
        printer.tick()
        printer.tick()
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f".{linesep}message..{linesep}"

    def test_ticks_spam_control(self, printer, capfd, monkeypatch):
        monkeypatch.setattr("neuromation.cli.printer.TICK_TIMEOUT", 1000)
        printer.tick()
        printer.tick()
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f".{linesep}"


class TestTTYPrinter:
    @pytest.fixture
    def printer(self, click_tty_emulation):
        return TTYPrinter()

    def test_no_messages(self, capfd, printer):
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == ""

    def test_one_message(self, capfd, printer):
        printer.print("message")
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f"message{linesep}"

    def test_two_messages(self, capfd, printer):
        printer.print("message1")
        printer.print("message2")
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert out == f"message1{linesep}message2{linesep}"

    # very simple test
    def test_message_lineno(self, printer, capfd):
        printer.print("message1")
        printer.print("message1-replace", 1)
        printer.print("message3", 3)
        printer.close()
        out, err = capfd.readouterr()
        assert err == ""
        assert "message1" in out
        assert "message1-replace" in out
        assert "message3" in out
        assert CSI in out
