"""Desktop capture backend with temporary, restored screenshot palette settings."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import struct
import tempfile
import time
import zlib

SUPPORTED = {"EDUX1052A", "EDUX1052G", "DSOX1202A", "DSOX1202G", "DSOX1204A", "DSOX1204G"}
MAX_IMAGE = 20 * 1024 * 1024


@dataclass(frozen=True)
class Device:
    host: str
    vendor: str
    model: str
    serial: str
    firmware: str = ""

    @property
    def supported(self):
        return ("KEYSIGHT" in self.vendor.upper() or "AGILENT" in self.vendor.upper()) and self.model.upper() in SUPPORTED

    @property
    def identity(self):
        return self.vendor.upper(), self.model.upper(), self.serial.upper()


def parse_identity(host, reply):
    parts = reply.strip().split(",", 3)
    if len(parts) != 4 or not all(p.strip() for p in parts[:3]):
        raise ValueError("儀器未回覆有效的型號與序號。")
    return Device(host, *(p.strip() for p in parts))


class Connection:
    def __init__(self, host, timeout=10, port=5025):
        # Literal addresses prevent accidental DNS delays in discovery.
        self.host = str(ipaddress.IPv4Address(host))
        self.sock = socket.create_connection((self.host, port), timeout)
        self.deadline = time.monotonic() + timeout
        self.broken = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.sock.close()

    def read(self, n):
        data = bytearray()
        while len(data) < n:
            left = self.deadline - time.monotonic()
            if left <= 0:
                self.broken = True
                raise TimeoutError("儀器回覆逾時。")
            self.sock.settimeout(left)
            try:
                chunk = self.sock.recv(n - len(data))
            except OSError:
                self.broken = True
                raise
            if not chunk:
                self.broken = True
                raise ConnectionError("儀器在資料傳完前中斷連線。")
            data.extend(chunk)
        return bytes(data)

    def write(self, command):
        try:
            self.sock.sendall((command + "\n").encode("ascii"))
        except OSError:
            self.broken = True
            raise

    def query(self, command):
        self.write(command)
        reply = bytearray()
        while len(reply) < 2048:
            c = self.read(1)
            if c == b"\n":
                return reply.decode("ascii", errors="replace").strip()
            reply.extend(c)
        self.broken = True
        raise ValueError("儀器文字回覆過長。")

    def identify(self):
        return parse_identity(self.host, self.query("*IDN?"))

    def inksaver(self):
        value = self.query(":HARDcopy:INKSaver?")
        if value not in ("0", "1"):
            raise ValueError("儀器未回覆有效的截圖背景設定。")
        return value

    def set_inksaver(self, value):
        self.write(f":HARDcopy:INKSaver {value}")
        if self.inksaver() != value:
            raise ValueError("儀器未套用指定的截圖背景設定。")

    def image_with_background(self, background):
        if background not in ("black", "white"):
            raise ValueError("截圖背景必須是 black 或 white。")
        original = self.inksaver()
        desired = "0" if background == "black" else "1"
        if desired == original:
            return self.image()
        try:
            self.set_inksaver(desired)
            return self.image()
        except Exception as exc:
            if self.broken:
                raise RuntimeError("截圖連線中斷或回覆不完整，未繼續傳送還原指令。儀器的省墨設定可能已改變，請在面板確認。") from exc
            raise
        finally:
            # Never send anything after a timeout or incomplete binary response.
            if not self.broken:
                self.deadline = time.monotonic() + 4
                try:
                    self.set_inksaver(original)
                except Exception as exc:
                    raise RuntimeError("無法確認已還原儀器的省墨設定；請在面板確認後重試截圖。") from exc

    def image(self):
        self.write(":DISPlay:DATA? PNG, COLor")
        self.broken = True  # Unsafe to issue more commands until the block is consumed.
        if self.read(1) != b"#":
            raise ValueError("儀器未回覆 PNG 資料，請確認型號與遠端控制設定。")
        digit = self.read(1)
        if digit not in b"123456789":
            raise ValueError("儀器回覆的資料長度格式錯誤。")
        raw_length = self.read(int(digit))
        if not raw_length.isdigit():
            raise ValueError("儀器回覆的資料長度格式錯誤。")
        length = int(raw_length)
        if not 0 < length <= MAX_IMAGE:
            raise ValueError("儀器回覆的圖片大小異常。")
        data = self.read(length)
        terminator = self.read(1)
        if terminator == b"\r":
            terminator = self.read(1)
        if terminator != b"\n":
            raise ValueError("圖片資料結尾格式錯誤。")
        self.broken = False
        validate_png(data)
        return data


def validate_png(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("收到的資料不是 PNG 圖片。")
    pos, seen_header, seen_data = 8, False, False
    while pos + 12 <= len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        end = pos + 12 + length
        if end > len(data):
            break
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        crc = struct.unpack_from(">I", data, pos + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            raise ValueError("圖片資料校驗失敗，請重新截圖。")
        if not seen_header:
            if kind != b"IHDR" or length != 13 or not all(struct.unpack_from(">II", payload)):
                raise ValueError("PNG 圖片標頭無效。")
            seen_header = True
        if kind == b"IDAT":
            seen_data = True
        if kind == b"IEND" and length == 0 and seen_data and end == len(data):
            return
        pos = end
    raise ValueError("圖片資料不完整，請重新截圖。")


def probe(host, timeout=1.2, port=5025):
    with Connection(host, timeout, port) as conn:
        return conn.identify()


def scan(network, cancel, report, port=5025):
    net = ipaddress.ip_network(network.strip(), strict=False)
    if net.version != 4 or net.prefixlen < 22:
        raise ValueError("請輸入 IPv4 網段，範圍最多 1024 個位址，例如 192.168.1.0/24。")
    hosts = list(net.hosts())

    def check(host):
        if cancel.is_set():
            return None
        try:
            return probe(str(host), port=port)
        except (OSError, ValueError):
            return None

    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(check, host) for host in hosts]
        for done, future in enumerate(as_completed(futures), 1):
            if cancel.is_set():
                for pending in futures:
                    pending.cancel()
                break
            report(done, len(hosts), future.result())


def suggested_networks():
    try:
        addresses = {r[4][0] for r in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
        return sorted({str(ipaddress.ip_network(a + "/24", strict=False)) for a in addresses
                       if not ipaddress.ip_address(a).is_loopback and not ipaddress.ip_address(a).is_link_local})
    except OSError:
        return []


def capture(device, folder, port=5025, background=None):
    if not device.supported:
        raise ValueError("這個型號尚未支援截圖。目前支援 Keysight EDUX1052A/G、DSOX1202A/G、DSOX1204A/G。")
    with Connection(device.host, timeout=15, port=port) as conn:
        actual = conn.identify()
        if actual.identity != device.identity:
            raise ValueError("這個 IP 的儀器與記住的型號／序號不同。請重新搜尋並選擇正確的示波器。")
        data = conn.image() if background is None else conn.image_with_background(background)
    folder = Path(folder).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    safe = lambda s: re.sub(r"[^A-Za-z0-9_-]", "_", s)[:60]
    name = f"{datetime.now():%Y%m%d_%H%M%S_%f}_{safe(device.model)}_{safe(device.serial)}.png"
    path = folder / name
    # Never publish a partial image; never overwrite an earlier capture.
    fd, temp = tempfile.mkstemp(prefix=".scope-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.rename(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return path


def settings_path():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ScopeCapture" / "settings.json"


def load_settings(path=None):
    try:
        doc = json.loads((path or settings_path()).read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            return {}
        result = {k: doc[k] for k in ("network", "folder") if isinstance(doc.get(k), str)}
        if doc.get("language") in ("zh_TW", "en"):
            result["language"] = doc["language"]
        if isinstance(doc.get("auto_open"), bool):
            result["auto_open"] = doc["auto_open"]
        if doc.get("background") in ("black", "white"):
            result["background"] = doc["background"]
        if isinstance(doc.get("selected"), dict):
            d = Device(**doc["selected"])
            ipaddress.IPv4Address(d.host)
            if all(isinstance(v, str) for v in asdict(d).values()):
                result["selected"] = asdict(d)
        return result
    except (OSError, ValueError, TypeError):
        return {}


def save_settings(settings, path=None):
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
