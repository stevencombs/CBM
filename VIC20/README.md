# Commodore VIC-20 programs

Each program is a folder:

```
VIC20/<name>/
  README.md
  src/          ; .bas (BASIC 2.0) or .asm (64tass)
  export/       ; .prg and .d64
```

Default machine is **unexpanded 3.5K** (VICE `-memory none`), BASIC at `$1001` (4097).

If a listing runs out of memory, rebuild with `8k` / `16k` / `24k` / `all`. Those configs start BASIC at `$1201` (4609). The +3K expansion starts BASIC at `$0401` (1025).

## Zed (beta)

Open **this folder** as the workspace:

```bash
~/CBM/scripts/retro vic20
```

Install and tasks: [`../zed/vic20-basic/README.md`](../zed/vic20-basic/README.md).
