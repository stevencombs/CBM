# hello

MEGA65 BASIC65. Clears the screen and prints a short hello.

- Load address: `$2001` (petcat `-w65`)
- Source: `src/hello.bas` (same `.bas` as VIC-20/C64; this folder still tokenizes with `petcat -w65`)
- **MEGA65: Push to hardware** — `~/m65tools/etherload` (Ethernet)
- **MEGA65: Push+run on hardware** — `etherload -r`
- **MEGA65: Push to XEMU** / **Run in XEMU** — `/Applications/xmega65.app -prg`
