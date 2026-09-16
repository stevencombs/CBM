# hello

VIC-20 unexpanded (3.5K) BASIC 2.0. Clears to a black screen, then prints **HELLO** with each letter a different colour (`{red}` `{cyn}` `{pur}` `{grn}` `{yel}`).

- Load address: `$1001` (4097)
- VICE: `-memory none`
- Screen register: `36879` (`$900F`) — value 8 is black background
- Cursor colour restored to white (`POKE 646,1`)
- Source: `src/hello.bas`
- Hardware: `export/hello.prg` or `export/hello.d64` on SD2IEC / Pi1541
