# MEGA65 programs

Each program is a folder:

```
MEGA65/<name>/
  README.md
  src/          ; .bas (BASIC65 — same extension as VIC-20/C64)
  export/       ; .prg
```

Open **this folder** as the workspace (not `C64/` or `VIC20/`):

```bash
~/CBM/scripts/retro mega65
```

Then command palette → **task: spawn**. You should see:

- **MEGA65: Check listing**
- **MEGA65: Run in XEMU**
- **MEGA65: Push to XEMU**
- **MEGA65: Push to hardware** (`~/m65tools/etherload`)
- **MEGA65: Push+run on hardware** (`etherload -r`)

Listing language is **CBM BASIC** (Install Dev Extension → `~/CBM/zed/cbm-basic`). Theme **MEGA65 Dark**. Type `wht` then Tab for `{wht}`. Grok stays on the bottom. You press Push; Grok does not.
