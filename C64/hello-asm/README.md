# hello-asm

Commodore 64 6502 hello: flash the border (`INC $D020`).

- BASIC stub at `$0801`; code at `$0810` (`SYS 2064`)
- Source: `src/hello-asm.asm`
- Build: `64tass --cbm-prg`
- Hardware: copy `export/hello-asm.prg` or `export/hello-asm.d64` to an SD card for SD2IEC / Pi1541.
