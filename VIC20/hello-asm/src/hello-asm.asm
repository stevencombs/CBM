; VIC-20 unexpanded — SYS 4112 ($1010). Flash the border/aux nibble at $900F.
        * = $1001
        .word endsys, 2026
        .byte $9e
        .text "4112"
        .byte 0
endsys  .word 0

        * = $1010
start   ldx #0
        ldy #0
wait    inx
        bne wait
        iny
        bne wait
        inc $900f
        jmp start
