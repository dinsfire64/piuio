import curses
import mmap
import os
import time
import glob

DEVICE = "/dev/piuio_full0"
NUM_INPUTS = 4 * 8

for path in glob.glob("/dev/input/js*"):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        print("opened", path)
        break
    except PermissionError:
        pass

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    fd = os.open(DEVICE, os.O_RDONLY)

    try:
        mm = mmap.mmap(
            fd,
            mmap.PAGESIZE,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ,
        )

        try:
            while True:
                inputs = mm[:NUM_INPUTS]

                stdscr.erase()

                for i in range(0, NUM_INPUTS, 8):
                    chunk = inputs[i:i + 8]

                    line = f"{i // 8:02d}: " + " ".join(
                        f"{value:02x}" for value in chunk
                    )

                    stdscr.addstr(i // 8, 0, line)

                stdscr.refresh()

                # Press q to quit
                key = stdscr.getch()
                if key == ord("q"):
                    break

                time.sleep(0.01)

        finally:
            mm.close()

    finally:
        os.close(fd)


curses.wrapper(main)