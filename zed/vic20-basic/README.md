# VIC-20 BASIC (Zed) — beta

Listing on the left (cyan boot-screen paper, blue ink, Source Code Pro). Grok on the right (black glass, green phosphor). You review the `.bas` before anything hits VICE or the SD card.

## Install (once)

```bash
~/CBM/scripts/install-vic20-zed.sh
```

Then in Zed: **zed: extensions → Install Dev Extension** → `~/CBM/zed/vic20-basic`.

Open the machine folder (not `~/CBM`):

```bash
~/CBM/scripts/retro vic20
```

Theme **VIC-20 Cyan** and font **Source Code Pro** come from `VIC20/.zed/settings.json`. Autosave is 1 second.

## Grok on the right

The listing is the cyan TV. Grok is the phosphor teletype on the **right dock** — it does not open by itself.

Zed 1.20 draws ACP chat on `editor.background` (the cyan listing). Green-on-cyan is unreadable. Grok on the right is therefore a **Terminal Thread** (black glass, green type):

1. **⌘?** or **⌘⇧G** — Agent Panel.
2. **+** → **New Terminal Thread** (this workspace starts Grok via `terminal_init_command`).
3. That pane is the Grok Build TUI. `vice` MCP still applies. **Push** stays your Zed task.

Do not use **Grok Build** in the ACP chat thread on this Zed version — that surface inherits the cyan paper. The TUI is the teletype we designed.

## Tokens

In a `.bas` buffer type `red`, `clr`, `cyn`, `yel`… then Tab. Or `{` and complete. Eight VIC colours only — no orange/greys. Spellings are `petcat`’s (`{rght}`, `{rvon}`, `{rvof}`).

## Tasks (command palette → `task: spawn`)

| Task | What |
|------|------|
| **VIC-20: Check listing** | `petcat -w2 -l 1001` + D64. No emulator. |
| **VIC-20: Run in VICE** | Check, then `xvic` NTSC unexpanded. |
| **VIC-20: Push** | Copy PRG/D64 to `VIC20/sdcard/` (you press this). |
| **VIC-20: Push+run** | Same copy. You still type `RUN` on the real VIC. |

Grok does not Push. Point `sdcard/` at your Pi1541/SD2IEC card (see that folder’s README).

## Homebrew `petcat`

These tasks call `/opt/homebrew/bin/petcat` (VICE). They must not use `~/.retrocombs-m65/bin/petcat` (BASIC65).
