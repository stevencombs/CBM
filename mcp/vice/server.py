#!/usr/bin/env python3
"""MCP server: tokenize, assemble, and drive VICE for C64 / VIC-20 work."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from binmon import BinMon, BinMonError, wait_for_port
from pngutil import write_rgb_png

ROOT = Path(os.environ.get("CBM_ROOT", Path.home() / "CBM")).expanduser().resolve()
STATE_DIR = ROOT / ".vice"
PID_FILE = STATE_DIR / "vice.pid"
SHOT_FILE = STATE_DIR / "screen.png"
MONITOR_HOST = os.environ.get("VICE_MONITOR_HOST", "127.0.0.1")
MONITOR_PORT = int(os.environ.get("VICE_MONITOR_PORT", "6502"))

MACHINES = {
    "c64": {
        "dir": "C64",
        "bin": "x64sc",
        "title": "Commodore 64",
        "default_memory": "",
        "screen": (0x0400, 40, 25),
    },
    "vic20": {
        "dir": "VIC20",
        "bin": "xvic",
        "title": "Commodore VIC-20",
        "default_memory": "none",
        "screen": (0x1E00, 22, 23),
    },
}
VIC_MEMORY = ("none", "3k", "8k", "16k", "24k", "all")
LOAD_ADDR = {
    ("c64", ""): 0x0801,
    ("c64", "none"): 0x0801,
    ("vic20", "none"): 0x1001,
    ("vic20", "3k"): 0x0401,
    ("vic20", "8k"): 0x1201,
    ("vic20", "16k"): 0x1201,
    ("vic20", "24k"): 0x1201,
    ("vic20", "all"): 0x1201,
}

mcp = MCPServer(
    "vice",
    version="0.1.0",
    instructions=(
        "Drive VICE for Commodore 64 and VIC-20. Write source under "
        f"{ROOT}/C64/<program> or {ROOT}/VIC20/<program>, tokenize or assemble "
        "to a PRG, then load (autostart injects the PRG — do not type listings). "
        "type_keys is for READY-prompt commands only (LIST, RUN, SYS). "
        "Default VIC-20 memory is unexpanded 3.5K (none). NTSC. "
        "After load, screenshot or screen_text to see the result. "
        "export_d64 for SD2IEC / Pi1541. C64 Ultimate LAN push is not wired yet."
    ),
)


class Runtime:
    proc: subprocess.Popen[bytes] | None = None
    mon: BinMon | None = None
    machine: str | None = None
    memory: str = "none"


RT = Runtime()


def _tool_error(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(exc)}


def brew_prefix() -> Path:
    brew = shutil.which("brew")
    if brew:
        return Path(brew).resolve().parent.parent
    for candidate in (Path("/opt/homebrew"), Path("/usr/local")):
        if (candidate / "bin" / "x64sc").exists():
            return candidate
    return Path("/opt/homebrew")


def gtk_env() -> dict[str, str]:
    """Homebrew GTK/VICE needs GSettings schemas or x64sc aborts at launch."""
    env = os.environ.copy()
    share = str(brew_prefix() / "share")
    env.setdefault("GSETTINGS_SCHEMA_DIR", str(Path(share) / "glib-2.0" / "schemas"))
    xdg = [p for p in env.get("XDG_DATA_DIRS", "").split(":") if p]
    if share not in xdg:
        env["XDG_DATA_DIRS"] = ":".join([share, *xdg] or [share, "/usr/local/share", "/usr/share"])
    env.setdefault("GDK_BACKEND", "quartz")
    return env


def which_vice(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(
            f"{name} not found on PATH. Install VICE (brew install vice) "
            "and ensure /opt/homebrew/bin is on PATH."
        )
    return path


def which_tool(name: str, hint: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} not found on PATH. {hint}")
    return path


def norm_machine(machine: str) -> str:
    key = machine.strip().lower().replace("-", "").replace(" ", "")
    aliases = {
        "c64": "c64",
        "commodore64": "c64",
        "x64": "c64",
        "x64sc": "c64",
        "vic20": "vic20",
        "vic": "vic20",
        "xvic": "vic20",
    }
    if key not in aliases:
        raise ValueError("machine must be c64 or vic20")
    return aliases[key]


def norm_memory(machine: str, memory: str) -> str:
    if machine == "c64":
        return ""
    mem = (memory or "none").strip().lower()
    if mem in ("3.5k", "3.5", "unexpanded", "default", ""):
        mem = "none"
    if mem not in VIC_MEMORY:
        raise ValueError(f"VIC-20 memory must be one of {list(VIC_MEMORY)}")
    return mem


def load_address(machine: str, memory: str) -> int:
    mem = norm_memory(machine, memory)
    return LOAD_ADDR[(machine, mem)]


def machine_dir(machine: str) -> Path:
    path = ROOT / MACHINES[machine]["dir"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_name(name: str) -> str:
    n = name.strip()
    if not re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,46}[a-z0-9])?", n):
        raise ValueError(
            "program name must be 2–48 chars, lowercase letters, digits, hyphens"
        )
    return n


def program_dir(machine: str, name: str) -> Path:
    return machine_dir(machine) / validate_name(name)


def parse_addr(value: str | int) -> int:
    if isinstance(value, int):
        return value & 0xFFFF
    s = str(value).strip().lower().replace("_", "")
    if s.startswith("$"):
        return int(s[1:], 16) & 0xFFFF
    if s.startswith("0x"):
        return int(s, 16) & 0xFFFF
    if re.fullmatch(r"[0-9a-f]{1,4}", s) and any(c in "abcdef" for c in s):
        return int(s, 16) & 0xFFFF
    return int(s, 10) & 0xFFFF


def parse_bytes(data: str | list[int]) -> bytes:
    if isinstance(data, list):
        return bytes(int(x) & 0xFF for x in data)
    s = str(data).strip()
    if not s:
        return b""
    parts = re.split(r"[\s,]+", s)
    out: list[int] = []
    for p in parts:
        if not p:
            continue
        if p.startswith("$"):
            out.append(int(p[1:], 16) & 0xFF)
        elif p.startswith("0x"):
            out.append(int(p, 16) & 0xFF)
        else:
            out.append(int(p, 16 if re.fullmatch(r"[0-9a-f]{2}", p.lower()) else 10) & 0xFF)
    return bytes(out)


def petscii_from_ascii(text: str) -> bytes:
    out = bytearray()
    i = 0
    tokens = {
        "return": 0x0D,
        "enter": 0x0D,
        "clr": 0x93,
        "home": 0x13,
        "down": 0x11,
        "up": 0x91,
        "left": 0x9D,
        "right": 0x1D,
        "del": 0x14,
        "inst": 0x94,
    }
    while i < len(text):
        if text[i] == "{" :
            end = text.find("}", i)
            if end == -1:
                out.append(0x7B)
                i += 1
                continue
            token = text[i + 1 : end].strip().lower()
            if token in tokens:
                out.append(tokens[token])
            elif token.startswith("chr$") or token.isdigit():
                num = int(re.sub(r"[^0-9]", "", token) or "0")
                out.append(num & 0xFF)
            i = end + 1
            continue
        ch = text[i]
        o = ord(ch)
        if ch in "\n\r":
            out.append(0x0D)
        elif 0x41 <= o <= 0x5A:
            out.append(o)
        elif 0x61 <= o <= 0x7A:
            out.append(o - 0x20)
        elif 0x20 <= o <= 0x5F:
            out.append(o)
        i += 1
    return bytes(out)


def screen_codes_to_text(data: bytes, cols: int) -> str:
    rows: list[str] = []
    for i in range(0, len(data), cols):
        row = data[i : i + cols]
        chars: list[str] = []
        for b in row:
            c = b & 0x7F
            if c < 0x20:
                chars.append(chr(ord("@") + c))
            elif c < 0x40:
                chars.append(chr(c))
            elif c < 0x60:
                chars.append(chr(ord("a") + (c - 0x40)))
            else:
                chars.append(".")
        rows.append("".join(chars).rstrip())
    while rows and not rows[-1].strip():
        rows.pop()
    return "\n".join(rows)


def cbm_filename(name: str) -> str:
    base = re.sub(r"[^a-z0-9]", "", name.lower())[:16]
    return base or "program"


def find_source(folder: Path, kind: str) -> Path:
    src = folder / "src"
    if not src.is_dir():
        raise FileNotFoundError(f"No src/ directory in {folder}")
    ext = ".bas" if kind == "basic" else ".asm"
    matches = sorted(src.glob(f"*{ext}"))
    if not matches:
        raise FileNotFoundError(f"No {ext} file in {src}")
    preferred = src / f"{folder.name}{ext}"
    return preferred if preferred in matches else matches[0]


def detect_kind(folder: Path) -> str:
    src = folder / "src"
    if (src / f"{folder.name}.bas").exists() or list(src.glob("*.bas")):
        return "basic"
    if (src / f"{folder.name}.asm").exists() or list(src.glob("*.asm")):
        return "asm"
    raise FileNotFoundError(f"No .bas or .asm in {src}")


def run_cmd(cmd: list[str], timeout: int = 60) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}): {err}")
    return (proc.stdout or "").strip()


def tokenize_file(machine: str, folder: Path, memory: str) -> Path:
    src = find_source(folder, "basic")
    export = folder / "export"
    export.mkdir(parents=True, exist_ok=True)
    dest = export / f"{folder.name}.prg"
    addr = load_address(machine, memory)
    petcat = which_tool("petcat", "Install VICE (brew install vice).")
    run_cmd(
        [
            petcat,
            "-w2",
            "-l",
            f"{addr:04x}",
            "-f",
            "-o",
            str(dest),
            "--",
            str(src),
        ]
    )
    return dest


def assemble_file(folder: Path) -> Path:
    src = find_source(folder, "asm")
    export = folder / "export"
    export.mkdir(parents=True, exist_ok=True)
    dest = export / f"{folder.name}.prg"
    tass = which_tool("64tass", "Install 64tass (brew install tass64).")
    run_cmd(
        [
            tass,
            "--cbm-prg",
            "-o",
            str(dest),
            "-l",
            str(export / f"{folder.name}.labels"),
            str(src),
        ]
    )
    return dest


def make_d64(folder: Path, disk_name: str = "") -> Path:
    prg = folder / "export" / f"{folder.name}.prg"
    if not prg.is_file():
        raise FileNotFoundError(f"No PRG at {prg}; tokenize or assemble first")
    dest = folder / "export" / f"{folder.name}.d64"
    label = (disk_name or cbm_filename(folder.name))[:16]
    ident = (cbm_filename(folder.name)[:2] or "cb").upper()
    c1541 = which_tool("c1541", "Install VICE (brew install vice).")
    run_cmd(
        [
            c1541,
            "-format",
            f"{label},{ident}",
            "d64",
            str(dest),
            "-attach",
            str(dest),
            "-write",
            str(prg),
            cbm_filename(folder.name),
        ]
    )
    return dest


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def saved_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None
    return pid if pid_alive(pid) else None


def kill_vice() -> None:
    if RT.mon is not None:
        try:
            RT.mon.quit()
        except Exception:
            RT.mon.close()
        RT.mon = None
    proc = RT.proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
    pid = saved_pid()
    if pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.4)
            if pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    RT.proc = None
    RT.machine = None
    if PID_FILE.exists():
        PID_FILE.unlink()


def attach_monitor() -> BinMon:
    if RT.mon is not None and RT.mon.connected:
        try:
            RT.mon.ping()
            return RT.mon
        except Exception:
            RT.mon.close()
            RT.mon = None
    mon = BinMon(MONITOR_HOST, MONITOR_PORT)
    mon.connect()
    mon.ping()
    RT.mon = mon
    return mon


def start_vice(machine: str, memory: str, autostart: Path | None = None) -> dict[str, Any]:
    kill_vice()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    binary = which_vice(MACHINES[machine]["bin"])
    cmd = [
        binary,
        "-binarymonitor",
        "-binarymonitoraddress",
        f"ip4://{MONITOR_HOST}:{MONITOR_PORT}",
        "-autostartprgmode",
        "1",
        "-autostart-warp",
        "+drive8truedrive",
        "-ntsc",
        "-chdir",
        str(machine_dir(machine)),
    ]
    if machine == "vic20":
        cmd.extend(["-memory", memory or "none", "-model", "vic20ntsc"])
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=open(STATE_DIR / "vice.stderr.log", "ab"),
        start_new_session=True,
        env=gtk_env(),
    )
    RT.proc = proc
    PID_FILE.write_text(str(proc.pid))
    RT.machine = machine
    RT.memory = memory or "none"
    try:
        wait_for_port(MONITOR_HOST, MONITOR_PORT, timeout=15.0)
        mon = attach_monitor()
        if autostart is not None:
            mon.autostart(str(autostart), run=True)
        try:
            mon.resume()
        except Exception:
            pass
    except Exception:
        kill_vice()
        raise
    return {
        "ok": True,
        "machine": machine,
        "memory": RT.memory,
        "pid": proc.pid,
        "monitor": f"{MONITOR_HOST}:{MONITOR_PORT}",
        "autostart": str(autostart) if autostart else None,
        "binary": binary,
    }


def require_monitor() -> BinMon:
    if RT.mon is None or not RT.mon.connected:
        if saved_pid() is None:
            raise RuntimeError("VICE is not running. Call start first.")
        return attach_monitor()
    return RT.mon


def after_run_resume(mon: BinMon) -> None:
    try:
        mon.resume()
    except BinMonError:
        pass


def program_readme(machine: str, name: str, kind: str, memory: str) -> str:
    title = MACHINES[machine]["title"]
    addr = load_address(machine, memory)
    src_name = f"{name}.bas" if kind == "basic" else f"{name}.asm"
    mem_note = (
        "Unexpanded 3.5K (VICE `-memory none`)."
        if machine == "vic20" and (memory or "none") == "none"
        else (f"VIC-20 memory: {memory}." if machine == "vic20" else "64K C64.")
    )
    how = (
        f"Tokenize with `petcat -w2 -l {addr:04x}` (BASIC 2.0)."
        if kind == "basic"
        else "Assemble with `64tass --cbm-prg`."
    )
    return (
        f"# {name}\n\n"
        f"{title} {'BASIC 2.0' if kind == 'basic' else '6502 assembly'} program.\n\n"
        f"- Load address: `${addr:04X}` ({addr} decimal)\n"
        f"- {mem_note}\n"
        f"- Source: `src/{src_name}`\n"
        f"- Build: {how}\n"
        f"- Hardware: copy `export/{name}.prg` or `export/{name}.d64` to an SD card "
        f"for SD2IEC / Pi1541. C64 Ultimate: same files on USB/SD.\n"
    )


@mcp.tool()
def start(machine: str, memory: str = "none") -> dict[str, Any]:
    """Launch VICE with a visible window and binary monitor. machine is c64 or vic20.

    VIC-20 memory: none (default 3.5K unexpanded), 3k, 8k, 16k, 24k, all. NTSC.
    """
    try:
        m = norm_machine(machine)
        mem = norm_memory(m, memory)
        return start_vice(m, mem)
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def stop() -> dict[str, Any]:
    """Quit VICE if it is running."""
    try:
        kill_vice()
        return {"ok": True, "stopped": True}
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def status() -> dict[str, Any]:
    """VICE process, machine, memory config, and monitor connection."""
    pid = saved_pid()
    info: dict[str, Any] = {
        "ok": True,
        "cbm_root": str(ROOT),
        "running": pid is not None,
        "pid": pid,
        "machine": RT.machine,
        "memory": RT.memory if RT.machine == "vic20" else None,
        "monitor": None,
    }
    if pid is None:
        return info
    try:
        mon = attach_monitor()
        info["monitor"] = mon.vice_info()
        info["banks"] = [b["name"] for b in mon.banks()]
        try:
            mon.resume()
        except Exception:
            pass
    except Exception as exc:
        info["monitor_error"] = str(exc)
    return info


@mcp.tool()
def list_programs(machine: str = "") -> dict[str, Any]:
    """List program folders under C64/ and/or VIC20/."""
    try:
        machines = [norm_machine(machine)] if machine.strip() else ["c64", "vic20"]
        out: dict[str, Any] = {"ok": True, "root": str(ROOT), "programs": []}
        for m in machines:
            base = machine_dir(m)
            for folder in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")):
                src = folder / "src"
                kinds = []
                if src.is_dir():
                    if list(src.glob("*.bas")):
                        kinds.append("basic")
                    if list(src.glob("*.asm")):
                        kinds.append("asm")
                prg = folder / "export" / f"{folder.name}.prg"
                d64 = folder / "export" / f"{folder.name}.d64"
                out["programs"].append(
                    {
                        "machine": m,
                        "name": folder.name,
                        "path": str(folder),
                        "kinds": kinds,
                        "prg": prg.is_file(),
                        "d64": d64.is_file(),
                    }
                )
        return out
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def new_program(
    machine: str,
    name: str,
    kind: str = "basic",
    memory: str = "none",
) -> dict[str, Any]:
    """Create ~/CBM/C64/<name> or ~/CBM/VIC20/<name> with src stub and README. kind is basic or asm."""
    try:
        m = norm_machine(machine)
        k = kind.strip().lower()
        if k not in ("basic", "asm"):
            raise ValueError("kind must be basic or asm")
        mem = norm_memory(m, memory)
        n = validate_name(name)
        folder = program_dir(m, n)
        if folder.exists():
            raise FileExistsError(f"Program already exists: {folder}")
        (folder / "src").mkdir(parents=True)
        (folder / "export").mkdir(parents=True)
        addr = load_address(m, mem)
        if k == "basic":
            title = "COMMODORE 64" if m == "c64" else "VIC-20 3.5K"
            src = folder / "src" / f"{n}.bas"
            src.write_text(
                "10 print chr$(147)\n"
                f'20 print "hello from cbm"\n'
                f'30 print "{title.lower()}"\n'
                "40 print\n"
                '50 print "ready."\n'
            )
        else:
            src = folder / "src" / f"{n}.asm"
            if m == "c64":
                src.write_text(
                    "; C64 — SYS 2064 ($0810)\n"
                    "        * = $0801\n"
                    "        .word endsys, 2026\n"
                    '        .byte $9e\n'
                    '        .text "2064"\n'
                    '        .byte 0\n'
                    "endsys  .word 0\n"
                    "        * = $0810\n"
                    "start   ldx #0\n"
                    "        ldy #0\n"
                    "wait    inx\n"
                    "        bne wait\n"
                    "        iny\n"
                    "        bne wait\n"
                    "        inc $d020\n"
                    "        jmp start\n"
                )
            else:
                src.write_text(
                    "; VIC-20 unexpanded — SYS 4112 ($1010)\n"
                    "        * = $1001\n"
                    "        .word endsys, 2026\n"
                    '        .byte $9e\n'
                    '        .text "4112"\n'
                    '        .byte 0\n'
                    "endsys  .word 0\n"
                    "        * = $1010\n"
                    "start   ldx #0\n"
                    "        ldy #0\n"
                    "wait    inx\n"
                    "        bne wait\n"
                    "        iny\n"
                    "        bne wait\n"
                    "        inc $900f\n"
                    "        jmp start\n"
                )
        (folder / "README.md").write_text(program_readme(m, n, k, mem))
        return {
            "ok": True,
            "machine": m,
            "name": n,
            "kind": k,
            "path": str(folder),
            "source": str(src),
            "load_address": f"${addr:04X}",
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def tokenize(machine: str, program: str, memory: str = "none") -> dict[str, Any]:
    """Tokenize src/*.bas with petcat BASIC 2.0 into export/<name>.prg."""
    try:
        m = norm_machine(machine)
        mem = norm_memory(m, memory)
        folder = program_dir(m, program)
        dest = tokenize_file(m, folder, mem)
        addr = load_address(m, mem)
        return {
            "ok": True,
            "prg": str(dest),
            "bytes": dest.stat().st_size,
            "load_address": f"${addr:04X}",
            "machine": m,
            "memory": mem or None,
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def assemble(machine: str, program: str) -> dict[str, Any]:
    """Assemble src/*.asm with 64tass --cbm-prg into export/<name>.prg."""
    try:
        m = norm_machine(machine)
        folder = program_dir(m, program)
        dest = assemble_file(folder)
        return {
            "ok": True,
            "prg": str(dest),
            "bytes": dest.stat().st_size,
            "labels": str(folder / "export" / f"{folder.name}.labels"),
            "machine": m,
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def export_d64(machine: str, program: str, disk_name: str = "") -> dict[str, Any]:
    """Build a 1541 .d64 in export/ for SD2IEC or Pi1541."""
    try:
        m = norm_machine(machine)
        folder = program_dir(m, program)
        dest = make_d64(folder, disk_name)
        return {
            "ok": True,
            "d64": str(dest),
            "bytes": dest.stat().st_size,
            "note": "Copy the D64 (or the PRG) onto the SD card for SD2IEC / Pi1541.",
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def load(
    machine: str,
    program: str,
    run: bool = True,
    memory: str = "none",
) -> dict[str, Any]:
    """Build if needed, then autostart the PRG in VICE (RAM inject, warp). Do not type the listing."""
    try:
        m = norm_machine(machine)
        mem = norm_memory(m, memory)
        folder = program_dir(m, program)
        kind = detect_kind(folder)
        prg = (
            tokenize_file(m, folder, mem)
            if kind == "basic"
            else assemble_file(folder)
        )
        need_restart = (
            RT.machine != m
            or (m == "vic20" and RT.memory != mem)
            or saved_pid() is None
        )
        if need_restart:
            start_vice(m, mem, autostart=prg)
        else:
            mon = require_monitor()
            mon.autostart(str(prg), run=run)
            if run:
                after_run_resume(mon)
        time.sleep(0.8 if kind == "basic" else 0.4)
        return {
            "ok": True,
            "machine": m,
            "memory": mem or None,
            "program": program,
            "kind": kind,
            "prg": str(prg),
            "run": run,
            "load_address": f"${load_address(m, mem):04X}",
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def type_keys(text: str) -> dict[str, Any]:
    """Type PETSCII into the keyboard buffer. Commands only (LIST, RUN, SYS 2064). Not for whole listings."""
    try:
        if len(text) > 80:
            return {
                "ok": False,
                "error": "type_keys is for short READY-prompt commands. Write a source file and load() it.",
            }
        mon = require_monitor()
        payload = petscii_from_ascii(text)
        if not payload.endswith(b"\x0d"):
            payload += b"\x0d"
        mon.keyboard_feed(payload)
        after_run_resume(mon)
        time.sleep(0.25)
        return {"ok": True, "typed": text, "bytes": len(payload)}
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def reset(hard: bool = False) -> dict[str, Any]:
    """Soft reset (default) or hard power-cycle the emulated machine."""
    try:
        mon = require_monitor()
        mon.reset(hard=hard)
        after_run_resume(mon)
        time.sleep(0.4)
        return {"ok": True, "hard": hard}
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def screenshot(delay_ms: int = 0) -> dict[str, Any]:
    """Capture the current VICE display to CBM/.vice/screen.png. Then read_file that PNG to see it."""
    try:
        if delay_ms > 0:
            time.sleep(min(delay_ms, 5000) / 1000.0)
        mon = require_monitor()
        disp = mon.display_get()
        palette = mon.palette_get()
        after_run_resume(mon)
        buf: bytes = disp["buffer"]
        dw = int(disp["debug_width"])
        dh = int(disp["debug_height"])
        xo = int(disp["x_offset"])
        yo = int(disp["y_offset"])
        iw = int(disp["inner_width"]) or dw
        ih = int(disp["inner_height"]) or dh
        if dw <= 0 or dh <= 0 or len(buf) < dw * dh:
            raise RuntimeError("VICE returned an empty display buffer")
        rgb = bytearray(iw * ih * 3)
        fallback = (0, 0, 0)
        for y in range(ih):
            src_y = yo + y
            for x in range(iw):
                src_x = xo + x
                if 0 <= src_x < dw and 0 <= src_y < dh:
                    idx = buf[src_y * dw + src_x]
                    color = palette[idx] if idx < len(palette) else fallback
                else:
                    color = fallback
                off = (y * iw + x) * 3
                rgb[off : off + 3] = bytes(color)
        write_rgb_png(SHOT_FILE, iw, ih, bytes(rgb))
        return {
            "ok": True,
            "path": str(SHOT_FILE),
            "width": iw,
            "height": ih,
            "note": "Read this PNG with read_file to see the screen.",
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def screen_text() -> dict[str, Any]:
    """Dump the text screen (screen codes → ASCII). C64 40x25 at $0400; VIC-20 unexpanded 22x23 at $1E00."""
    try:
        mon = require_monitor()
        machine = RT.machine or "c64"
        mem = RT.memory if machine == "vic20" else ""
        if machine == "vic20" and mem not in ("", "none"):
            start, cols, rows = (0x1000, 22, 23)
        else:
            start, cols, rows = MACHINES[machine]["screen"]
        data = mon.mem_get(start, start + cols * rows - 1)
        after_run_resume(mon)
        text = screen_codes_to_text(data, cols)
        return {
            "ok": True,
            "machine": machine,
            "address": f"${start:04X}",
            "cols": cols,
            "rows": rows,
            "text": text,
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def peek(address: str, length: int = 16) -> dict[str, Any]:
    """Read memory. address as $d020, 0xd020, or 53280. length 1–256."""
    try:
        n = max(1, min(256, int(length)))
        start = parse_addr(address)
        end = (start + n - 1) & 0xFFFF
        mon = require_monitor()
        data = mon.mem_get(start, end)
        after_run_resume(mon)
        hex_bytes = " ".join(f"{b:02X}" for b in data)
        return {
            "ok": True,
            "address": f"${start:04X}",
            "length": len(data),
            "hex": hex_bytes,
            "bytes": list(data),
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def poke(address: str, data: str) -> dict[str, Any]:
    """Write bytes. data is hex like '00 01 FF' or '$00,$01'."""
    try:
        start = parse_addr(address)
        raw = parse_bytes(data)
        if not raw:
            raise ValueError("data is empty")
        if len(raw) > 256:
            raise ValueError("poke at most 256 bytes")
        mon = require_monitor()
        mon.mem_set(start, raw)
        after_run_resume(mon)
        return {
            "ok": True,
            "address": f"${start:04X}",
            "length": len(raw),
            "hex": " ".join(f"{b:02X}" for b in raw),
        }
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def registers() -> dict[str, Any]:
    """CPU registers (A, X, Y, PC, SP, flags)."""
    try:
        mon = require_monitor()
        regs = mon.registers()
        after_run_resume(mon)
        flags = int(regs.get("FL", 0))
        pretty = {
            "A": f"${int(regs.get('A', 0)):02X}",
            "X": f"${int(regs.get('X', 0)):02X}",
            "Y": f"${int(regs.get('Y', 0)):02X}",
            "PC": f"${int(regs.get('PC', 0)):04X}",
            "SP": f"${int(regs.get('SP', 0)):02X}",
            "NV-BDIZC": format(flags & 0xFF, "08b"),
        }
        return {"ok": True, "registers": pretty}
    except Exception as exc:
        return _tool_error(exc)


@mcp.tool()
def resume() -> dict[str, Any]:
    """Leave the VICE monitor and continue emulation."""
    try:
        mon = require_monitor()
        mon.resume()
        return {"ok": True}
    except Exception as exc:
        return _tool_error(exc)


if __name__ == "__main__":
    mcp.run(transport="stdio")
