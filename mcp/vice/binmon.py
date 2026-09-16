"""VICE 3.5+ binary monitor client (API v2, VICE 3.10).

Packet layout is from the VICE manual, chapter 13. There is no checksum.
Command length is the body only (not the command byte or request id).
"""

from __future__ import annotations

import socket
import struct
import time
from typing import Any

STX = 0x02
API = 0x02
EVENT_REQ_ID = 0xFFFFFFFF

CMD_MEM_GET = 0x01
CMD_MEM_SET = 0x02
CMD_REGISTERS_GET = 0x31
CMD_KEYBOARD_FEED = 0x72
CMD_PING = 0x81
CMD_BANKS_AVAILABLE = 0x82
CMD_DISPLAY_GET = 0x84
CMD_VICE_INFO = 0x85
CMD_PALETTE_GET = 0x91
CMD_EXIT = 0xAA
CMD_QUIT = 0xBB
CMD_RESET = 0xCC
CMD_AUTOSTART = 0xDD

RESP_JAM = 0x61
RESP_STOPPED = 0x62
RESP_RESUMED = 0x63

ERRORS = {
    0x00: "ok",
    0x01: "object does not exist",
    0x02: "invalid memspace",
    0x80: "wrong command length",
    0x81: "invalid parameter",
    0x82: "unknown API version",
    0x83: "unknown command",
    0x8F: "general failure",
}


class BinMonError(RuntimeError):
    def __init__(self, code: int, cmd: int, detail: str = ""):
        self.code = code
        msg = ERRORS.get(code, f"error 0x{code:02x}")
        extra = f" ({detail})" if detail else ""
        super().__init__(f"VICE monitor command 0x{cmd:02x}: {msg}{extra}")


class BinMon:
    def __init__(self, host: str = "127.0.0.1", port: int = 6502, timeout: float = 15.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self._req = 1
        self._banks: list[dict[str, Any]] | None = None
        self.last_events: list[dict[str, Any]] = []

    def connect(self) -> None:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        self.sock = sock
        self._req = 1
        self._banks = None

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    @property
    def connected(self) -> bool:
        return self.sock is not None

    def _send(self, cmd: int, body: bytes = b"") -> int:
        if self.sock is None:
            raise RuntimeError("Not connected to VICE binary monitor")
        req_id = self._req
        self._req = (self._req + 1) & 0x7FFFFFFF
        if self._req == 0:
            self._req = 1
        packet = (
            bytes([STX, API])
            + struct.pack("<I", len(body))
            + struct.pack("<I", req_id)
            + bytes([cmd])
            + body
        )
        self.sock.sendall(packet)
        return req_id

    def _recvall(self, n: int) -> bytes:
        if self.sock is None:
            raise RuntimeError("Not connected to VICE binary monitor")
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RuntimeError("VICE monitor connection closed")
            buf.extend(chunk)
        return bytes(buf)

    def _read_packet(self) -> tuple[int, int, int, bytes]:
        hdr = self._recvall(12)
        if hdr[0] != STX:
            raise RuntimeError(f"VICE monitor desync (got 0x{hdr[0]:02x}, expected STX)")
        body_len = struct.unpack_from("<I", hdr, 2)[0]
        resp_type = hdr[6]
        error = hdr[7]
        req_id = struct.unpack_from("<I", hdr, 8)[0]
        body = self._recvall(body_len) if body_len else b""
        return resp_type, error, req_id, body

    def transact(self, cmd: int, body: bytes = b"", timeout: float | None = None) -> bytes:
        req_id = self._send(cmd, body)
        deadline = time.time() + (timeout or self.timeout)
        self.last_events = []
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError(f"VICE monitor timed out waiting for 0x{cmd:02x}")
            assert self.sock is not None
            self.sock.settimeout(remaining)
            resp_type, error, got_id, resp_body = self._read_packet()
            if got_id == EVENT_REQ_ID:
                self.last_events.append(
                    {"type": resp_type, "error": error, "body": resp_body.hex()}
                )
                continue
            if got_id != req_id:
                continue
            if error != 0:
                raise BinMonError(error, cmd)
            return resp_body

    def ping(self) -> None:
        self.transact(CMD_PING)

    def vice_info(self) -> dict[str, Any]:
        body = self.transact(CMD_VICE_INFO)
        ml = body[0]
        main = list(body[1 : 1 + ml])
        sl = body[1 + ml]
        svn = body[2 + ml : 2 + ml + sl]
        rev = int.from_bytes(svn, "little") if svn else 0
        version = ".".join(str(x) for x in main) if main else "unknown"
        return {"version": version, "svn": rev}

    def banks(self) -> list[dict[str, Any]]:
        if self._banks is not None:
            return self._banks
        body = self.transact(CMD_BANKS_AVAILABLE)
        count = struct.unpack_from("<H", body, 0)[0]
        off = 2
        out: list[dict[str, Any]] = []
        for _ in range(count):
            item_size = body[off]
            off += 1
            chunk = body[off : off + item_size]
            off += item_size
            bank_id = struct.unpack_from("<H", chunk, 0)[0]
            nlen = chunk[2]
            name = chunk[3 : 3 + nlen].decode("ascii", "replace")
            out.append({"id": bank_id, "name": name})
        self._banks = out
        return out

    def bank_id(self, name: str = "cpu") -> int:
        banks = self.banks()
        want = name.lower()
        for bank in banks:
            if bank["name"].lower() == want:
                return int(bank["id"])
        if banks:
            return int(banks[0]["id"])
        return 0

    def mem_get(
        self,
        start: int,
        end: int,
        *,
        memspace: int = 0,
        bank: int | None = None,
        side_effects: bool = False,
    ) -> bytes:
        if end < start:
            raise ValueError("end address is before start")
        if bank is None:
            bank = self.bank_id("cpu")
        body = struct.pack(
            "<BHHBH", 1 if side_effects else 0, start & 0xFFFF, end & 0xFFFF, memspace, bank
        )
        resp = self.transact(CMD_MEM_GET, body)
        n = struct.unpack_from("<H", resp, 0)[0]
        data = resp[2 : 2 + n]
        if n == 0 and start == 0 and end == 0xFFFF:
            data = resp[2:]
        return data

    def mem_set(
        self,
        start: int,
        data: bytes,
        *,
        memspace: int = 0,
        bank: int | None = None,
        side_effects: bool = True,
    ) -> None:
        if not data:
            return
        if bank is None:
            bank = self.bank_id("cpu")
        end = (start + len(data) - 1) & 0xFFFF
        body = (
            struct.pack(
                "<BHHBH",
                1 if side_effects else 0,
                start & 0xFFFF,
                end,
                memspace,
                bank,
            )
            + data
        )
        self.transact(CMD_MEM_SET, body)

    def registers(self, memspace: int = 0) -> dict[str, int]:
        body = self.transact(CMD_REGISTERS_GET, bytes([memspace]))
        count = struct.unpack_from("<H", body, 0)[0]
        off = 2
        raw: dict[int, int] = {}
        for _ in range(count):
            item_size = body[off]
            off += 1
            chunk = body[off : off + item_size]
            off += item_size
            rid = chunk[0]
            val = struct.unpack_from("<H", chunk, 1)[0]
            raw[rid] = val
        names = {0: "A", 1: "X", 2: "Y", 3: "PC", 4: "SP", 5: "FL"}
        out = {names.get(i, f"r{i}"): v for i, v in raw.items()}
        out["_raw"] = raw  # type: ignore[assignment]
        return out

    def keyboard_feed(self, petscii: bytes) -> None:
        for i in range(0, len(petscii), 255):
            chunk = petscii[i : i + 255]
            self.transact(CMD_KEYBOARD_FEED, bytes([len(chunk)]) + chunk)

    def display_get(self) -> dict[str, Any]:
        body = self.transact(CMD_DISPLAY_GET, bytes([1, 0]), timeout=20.0)
        prefix_len = struct.unpack_from("<I", body, 0)[0]
        dw, dh, xo, yo, iw, ih = struct.unpack_from("<HHHHHH", body, 4)
        bpp = body[16]
        buf_len = struct.unpack_from("<I", body, 17)[0]
        buf = body[21 : 21 + buf_len]
        return {
            "debug_width": dw,
            "debug_height": dh,
            "x_offset": xo,
            "y_offset": yo,
            "inner_width": iw,
            "inner_height": ih,
            "bpp": bpp,
            "buffer": buf,
            "prefix_len": prefix_len,
        }

    def palette_get(self) -> list[tuple[int, int, int]]:
        body = self.transact(CMD_PALETTE_GET, bytes([1]))
        count = struct.unpack_from("<H", body, 0)[0]
        off = 2
        colors: list[tuple[int, int, int]] = []
        for _ in range(count):
            item_size = body[off]
            off += 1
            chunk = body[off : off + item_size]
            off += item_size
            colors.append((chunk[0], chunk[1], chunk[2]))
        return colors

    def reset(self, hard: bool = False) -> None:
        self.transact(CMD_RESET, bytes([1 if hard else 0]))

    def autostart(self, path: str, run: bool = True, file_index: int = 0) -> None:
        raw = path.encode("utf-8")
        if len(raw) > 255:
            raise ValueError("Path is longer than 255 bytes; move the project closer to $HOME")
        body = bytes([1 if run else 0]) + struct.pack("<HB", file_index, len(raw)) + raw
        self.transact(CMD_AUTOSTART, body, timeout=30.0)

    def resume(self) -> None:
        self.transact(CMD_EXIT)

    def quit(self) -> None:
        try:
            self.transact(CMD_QUIT, timeout=3.0)
        except (OSError, TimeoutError, RuntimeError):
            pass
        self.close()


def wait_for_port(host: str, port: int, timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return
        except OSError as exc:
            last = exc
            time.sleep(0.15)
    raise RuntimeError(f"VICE binary monitor did not open {host}:{port}: {last}")
