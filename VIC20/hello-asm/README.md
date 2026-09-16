# hello-asm

VIC-20 unexpanded 6502 hello: flash VIC register `$900F`.

- BASIC stub at `$1001`; code at `$1010` (`SYS 4112`)
- VICE: `-memory none`
- Source: `src/hello-asm.asm`
- Build: `64tass --cbm-prg`
- Hardware: copy `export/hello-asm.prg` or `export/hello-asm.d64` to an SD card for SD2IEC / Pi1541.
