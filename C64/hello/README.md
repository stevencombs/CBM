# hello

Commodore 64 BASIC 2.0. Clears to black, then prints **HELLO** with each letter a different colour (`{red}` `{cyn}` `{pur}` `{grn}` `{yel}`).

- Load address: `$0801` (2049)
- Border/background: `53280` / `53281` (`$D020` / `$D021`)
- Cursor colour restored to white (`POKE 646,1`)
- Source: `src/hello.bas`
- Hardware: `export/hello.prg` or `export/hello.d64` on SD2IEC / Pi1541 / C64 Ultimate USB
