import curses
import threading
from time import sleep


class HybridEchidnaDisplay:
    def __init__(self):
        self.active = False
        self.scr = None
        self.main_title = "Hybrid Echidna"  # Title of main window

    def start(self, scr):
        self.active = True
        self.scr = scr

    def update(self):
        if self.active:
            self.scr.erase()
            # Print border
            self.scr.border(0)
            # Write main title
            self.scr.addstr(
                0, curses.COLS // 2 - len(self.main_title) // 2, self.main_title
            )
            self.scr.refresh()

    def stop(self):
        self.active = False
        self.scr = None


display = HybridEchidnaDisplay()
display_thread = None


def _display():
    global display
    exc = None
    try:
        stdscr = curses.initscr()
        curses.noecho()
        display.start(stdscr)
        while display.active:
            display.update()
            sleep(1)
    except (Exception, KeyboardInterrupt) as e:
        exc = e

    display.stop()
    curses.echo()
    curses.endwin()
    if exc:
        raise exc


def _wrapper_display():
    curses.wrapper(_display)


def start_display():
    global display_thread
    if display_thread is None:
        display_thread = threading.Thread(target=_display, args=())
        display_thread.daemon = True
        display_thread.start()


def stop_display():
    global display_thread
    global display
    if not display_thread is None:
        display.stop()
        display_thread.join()  # Wait until it terminates
        display_thread = None
