; C64 — SYS 2064 ($0810). Flash the border.
        * = $0801
        .word endsys, 2026
        .byte $9e
        .text "2064"
        .byte 0
endsys  .word 0

        * = $0810
start   ldx #0
        ldy #0
wait    inx
        bne wait
        iny
        bne wait
        inc $d020
        jmp start
