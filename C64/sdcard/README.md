# SD2IEC / Pi1541 / C64 Ultimate drop folder

`C64: Push` and `C64: Push+run` copy `export/*.prg` and `export/*.d64` here.

Point this directory at your card, or copy from here onto it:

```bash
# example: replace with your mount
# ln -sfn /Volumes/PI1541 ~/CBM/C64/sdcard
```

Override the path with `CBM_PUSH_C64` if you prefer not to symlink.

On the C64:

```
LOAD"HELLO",8
RUN
```

C64 Ultimate: same files on USB/SD; pick the PRG in the File Browser. LAN DMA push is not wired yet.

Push+run cannot press RUN on a breadbin. Use **C64: Run in VICE** to watch it execute on the Mac.
