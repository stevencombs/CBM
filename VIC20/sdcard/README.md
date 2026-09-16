# SD2IEC / Pi1541 drop folder

`VIC-20: Push` and `VIC-20: Push+run` copy `export/*.prg` and `export/*.d64` here.

Point this directory at your card, or copy from here onto it:

```bash
# example: replace with your mount
# ln -sfn /Volumes/PI1541 ~/CBM/VIC20/sdcard
```

Override the path with `CBM_PUSH_VIC20` if you prefer not to symlink.

On the VIC-20:

```
LOAD"HELLO",8
RUN
```

Push+run cannot press RETURN on the real machine. Use **VIC-20: Run in VICE** to watch it execute on the Mac.
