"""Desktop backend tests with real local sockets, no instrument required."""
from dataclasses import asdict
import json
from pathlib import Path
import socketserver
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

from scopecapture.desktop_core import (Device, capture, load_settings, probe, save_settings,
                                scan, validate_png)


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


PNG = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))
DEVICE = Device("127.0.0.1", "KEYSIGHT TECHNOLOGIES", "EDUX1052A", "EXAMPLE123")


class FakeScope(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, identity=DEVICE, image=PNG, truncate=False, inksaver="1", reject_restore=False):
        self.commands = []
        self.inksaver = inksaver
        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                while command := self.rfile.readline():
                    outer.commands.append(command.strip())
                    if command == b"*IDN?\n":
                        self.wfile.write(f"{identity.vendor},{identity.model},{identity.serial},1.0\n".encode())
                        self.wfile.flush()
                    elif command == b":HARDcopy:INKSaver?\n":
                        self.wfile.write((outer.inksaver + "\n").encode())
                        self.wfile.flush()
                    elif command.startswith(b":HARDcopy:INKSaver "):
                        value = command.decode().strip().split()[-1]
                        if not (reject_restore and value == inksaver):
                            outer.inksaver = value
                    elif command == b":DISPlay:DATA? PNG, COLor\n":
                        n = str(len(image)).encode()
                        block = b"#" + str(len(n)).encode() + n + image
                        if truncate:
                            self.wfile.write(block[:-5])
                            self.wfile.flush()
                            return
                        # Deliberately fragmented TCP response, including its header.
                        for start in range(0, len(block), 3):
                            self.wfile.write(block[start:start + 3])
                            self.wfile.flush()
                        self.wfile.write(b"\n")
                        self.wfile.flush()
                        # Keep the connection available for restoring Ink Saver.

        super().__init__(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.shutdown()
        self.server_close()
        self.thread.join()

    @property
    def port(self):
        return self.server_address[1]


class DesktopTests(unittest.TestCase):
    def test_background_switches_and_restores(self):
        for background, original, desired in (("black", "1", "0"), ("white", "0", "1")):
            with self.subTest(background=background), FakeScope(inksaver=original) as server, tempfile.TemporaryDirectory() as directory:
                path = capture(DEVICE, directory, port=server.port, background=background)
                self.assertEqual(path.read_bytes(), PNG)
                self.assertEqual(server.inksaver, original)
                self.assertEqual(server.commands, [b"*IDN?", b":HARDcopy:INKSaver?",
                    f":HARDcopy:INKSaver {desired}".encode(), b":HARDcopy:INKSaver?",
                    b":DISPlay:DATA? PNG, COLor", f":HARDcopy:INKSaver {original}".encode(), b":HARDcopy:INKSaver?"])

    def test_matching_background_needs_no_writes(self):
        with FakeScope(inksaver="0") as server, tempfile.TemporaryDirectory() as directory:
            capture(DEVICE, directory, port=server.port, background="black")
            self.assertEqual(server.commands, [b"*IDN?", b":HARDcopy:INKSaver?", b":DISPlay:DATA? PNG, COLor"])

    def test_corrupt_complete_png_restores_background(self):
        with FakeScope(image=PNG[:-12], inksaver="1") as server, tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "不完整"):
                capture(DEVICE, directory, port=server.port, background="black")
            self.assertEqual(server.inksaver, "1")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_broken_transfer_does_not_send_restore(self):
        with FakeScope(truncate=True, inksaver="1") as server, tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "省墨設定可能已改變"):
                capture(DEVICE, directory, port=server.port, background="black")
            self.assertEqual(server.inksaver, "0")
            self.assertEqual(server.commands[-1], b":DISPlay:DATA? PNG, COLor")

    def test_restore_failure_reported(self):
        with FakeScope(inksaver="1", reject_restore=True) as server, tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "無法確認已還原"):
                capture(DEVICE, directory, port=server.port, background="black")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_probe_and_fragmented_capture(self):
        with FakeScope() as server, tempfile.TemporaryDirectory() as directory:
            device = probe("127.0.0.1", port=server.port)
            self.assertTrue(device.supported)
            path = capture(device, Path(directory) / "中文資料夾", port=server.port)
            self.assertEqual(path.read_bytes(), PNG)
            self.assertIn("EDUX1052A_EXAMPLE123", path.name)
            self.assertEqual(server.commands, [b"*IDN?", b"*IDN?", b":DISPlay:DATA? PNG, COLor"])

    def test_changed_instrument_is_not_captured(self):
        wrong = Device("127.0.0.1", DEVICE.vendor, DEVICE.model, "OTHER_SERIAL")
        with FakeScope(identity=wrong) as server, tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "序號不同"):
                capture(DEVICE, directory, port=server.port)
            self.assertEqual(server.commands, [b"*IDN?"])
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_truncated_transfer_never_leaves_image(self):
        with FakeScope(truncate=True) as server, tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ConnectionError):
                capture(DEVICE, directory, port=server.port)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_bad_png_never_saved(self):
        with FakeScope(image=b"not a PNG") as server, tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "不是 PNG"):
                capture(DEVICE, directory, port=server.port)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_corrupt_or_incomplete_png(self):
        validate_png(PNG)
        for data in (PNG[:-12], PNG[:40] + b"x" + PNG[41:]):
            with self.assertRaises(ValueError):
                validate_png(data)

    def test_settings_roundtrip_and_corrupt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = {"selected": asdict(DEVICE), "network": "192.168.1.0/24", "folder": "中文路徑", "auto_open": False, "background": "white", "language": "en"}
            save_settings(settings, path)
            self.assertEqual(load_settings(path), settings)
            for bad in ("broken", "[]", json.dumps({"selected": {"host": []}})):
                path.write_text(bad, encoding="utf-8")
                self.assertEqual(load_settings(path), {})

    def test_scan_and_cancel(self):
        reports = []
        with patch("scopecapture.desktop_core.probe", return_value=DEVICE) as mocked:
            scan("192.168.0.0/30", threading.Event(), lambda *args: reports.append(args))
            self.assertEqual(mocked.call_count, 2)
            self.assertEqual(len(reports), 2)
        cancelled = threading.Event()
        cancelled.set()
        with patch("scopecapture.desktop_core.probe") as mocked:
            scan("192.168.1.0/24", cancelled, lambda *args: None)
            mocked.assert_not_called()
        with self.assertRaises(ValueError):
            scan("192.168.0.0/16", threading.Event(), lambda *args: None)

    def test_unsupported_vendor_cannot_capture(self):
        other = Device("127.0.0.1", "OTHER", "EDUX1052A", "123")
        with patch("scopecapture.desktop_core.Connection") as conn:
            with self.assertRaisesRegex(ValueError, "尚未支援"):
                capture(other, ".")
            conn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
