# hello

Commodore 64 BASIC 2.0. Clears the screen to black, then prints **HELLO** with each letter a different colour (the eight VIC-20 colours, so the same idea runs on both machines).

| Letter | Colour | `CHR$` |
|--------|--------|--------|
| H | red | 28 |
| E | cyan | 159 |
| L | purple | 156 |
| L | green | 30 |
| O | yellow | 158 |

- Load address: `$0801` (2049)
- Border/background: `53280` / `53281` (`$D020` / `$D021`)
- Cursor colour restored to white (`POKE 646,1`) so `READY.` is readable
- Source: `src/hello.bas`
- Hardware: `export/hello.prg` or `export/hello.d64` on SD2IEC / Pi1541 / C64 Ultimate USB
