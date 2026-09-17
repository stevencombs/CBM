# C64 BASIC (Zed)

Same desk as the VIC-20: listing on the left (C64 boot-screen blue paper, light-blue ink, Source Code Pro). Grok in the bottom terminal (black glass, green phosphor). You review the `.bas` before anything hits VICE or the SD card.

## Install (once)

```bash
~/CBM/scripts/install-c64-zed.sh
```

Then in Zed: **zed: extensions → Install Dev Extension** → `~/CBM/zed/c64-basic`.

Open the machine folder (not `~/CBM`):

```bash
~/CBM/scripts/retro c64
```

Theme **C64 Blue** and font **Source Code Pro** come from `C64/.zed/settings.json`. Autosave is 1 second.

## Grok (bottom terminal)

The listing is the 64 TV. Grok is the phosphor teletype along the **bottom**. Zed 1.20 Agent chat uses the listing paper — leave that panel closed.

**⌘⇧G** or **⌘J** toggles the bottom terminal. **task: spawn → Grok Build** starts the TUI there. **Push** stays your Zed task.

## Tokens

In a `.bas` buffer type `red`, `clr`, `orng`, `lblu`… then Tab. Or `{` and complete. Sixteen C64 colours (the VIC eight plus orange, brown, light red/green/blue, greys) and F1–F8. Spellings are VICE `petcat` (`{rght}`, `{rvon}`, `{lred}`, `{gry1}`).

## Tasks (command palette → `task: spawn`)

| Task | What |
|------|------|
| **C64: Check listing** | `petcat -w2 -l 0801` + D64. No emulator. |
| **C64: Run in VICE** | Check, then `x64sc` NTSC. |
| **C64: Push** | Copy PRG/D64 to `C64/sdcard/` (you press this). |
| **C64: Push+run** | Same copy. You still type `RUN` on the real 64. |

Grok does not Push. Point `sdcard/` at your Pi1541/SD2IEC card or copy to a C64 Ultimate USB stick.

## Homebrew `petcat`

These tasks call `/opt/homebrew/bin/petcat` (VICE). They must not use `~/.retrocombs-m65/bin/petcat` (BASIC65).
