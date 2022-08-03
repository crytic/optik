import curses
import threading
from time import sleep


def generate_progress_bar(bar_len: int, current: int, max: int) -> str:
    fill_char = "\u2588"
    res = "|"
    fill_ratio = current / max
    fill_perc = int(100.0 * fill_ratio)
    filled_bar = fill_char * int(bar_len * fill_ratio)
    res += filled_bar
    res += " " * (bar_len - len(res))
    res += "|"
    res += f" {fill_perc}%"
    return res


class HybridEchidnaDisplay:
    def __init__(self):
        self.active = False
        self.scr = None
        # INFO
        self.main_title = "Hybrid Echidna"  # Title of main window
        self.mode = "-"
        self.iteration: int = 0
        self.corpus_size: int = 0
        self.current_task_msg = "Starting up ..."
        self.progress_bar_len = 40
        self.current_task_progress = (
            33,
            100,
        )  # tuple (curr, goal,)
        self.fuzz_win_title = "Fuzzer"
        self.fuzz_total_cases_cnt = 0
        self.fuzz_last_cases_cnt = 0
        self.fuzz_total_time = 0  # in ms
        self.sym_win_title = "Symbolic execution"
        self.sym_total_inputs_solved = 0
        self.sym_total_solver_timeouts = 0
        self.sym_curr_solver_timeout = "???"
        self.sym_time_solving_average = 0
        self.sym_path_contr_average = "???"
        # WINDOW SIZES
        self.global_win_x_ratio = 0.3
        self.global_win_y_lines = 3
        self.fuzz_win_x_ratio = 0.3
        self.fuzz_win_y_lines = 4

    def start(self, scr):
        self.active = True
        self.scr = scr

    def update(self):
        if self.active:
            try:
                self.scr.erase()
                # Print border
                self.scr.border(0)
                # Write main title
                self.scr.addstr(
                    0,
                    curses.COLS // 2 - len(self.main_title) // 2,
                    self.main_title,
                    curses.A_BOLD,
                )
                # Global info window
                global_win = self.scr.derwin(
                    self.global_win_y_lines * 2 - 1,
                    int(curses.COLS * self.global_win_x_ratio),
                    0,
                    1,
                )
                global_win.addstr(1, 1, f"Iteration: #{self.iteration}")
                global_win.addstr(2, 1, f"Mode: {self.mode}")
                global_win.addstr(3, 1, f"Corpus size: {self.corpus_size}")
                # Current info window
                glob_lines, glob_cols = global_win.getmaxyx()
                current_win = self.scr.derwin(
                    glob_lines, curses.COLS - 1 - glob_cols, 0, glob_cols
                )
                current_win.addstr(
                    1,
                    (current_win.getmaxyx()[1] - len(self.current_task_msg))
                    // 2,
                    self.current_task_msg,
                )
                progress_bar = generate_progress_bar(
                    self.progress_bar_len,
                    *self.current_task_progress,
                )
                current_win.addstr(
                    2,
                    (current_win.getmaxyx()[1] - len(progress_bar)) // 2,
                    progress_bar,
                )
                # Fuzzer window
                fuzz_win = self.scr.derwin(
                    self.fuzz_win_y_lines * 2 - 1,
                    int(curses.COLS * self.fuzz_win_x_ratio),
                    glob_lines - 1,
                    1,
                )
                fuzz_lines, fuzz_cols = fuzz_win.getmaxyx()
                fuzz_win.border(" ", " ", 0, " ", " ", " ", " ", " ")
                fuzz_win.addstr(
                    0,
                    (fuzz_cols - len(self.fuzz_win_title)) // 2,
                    self.fuzz_win_title,
                    curses.A_BOLD,
                )
                fuzz_win.addstr(
                    1, 1, f"Tests found (total): {self.fuzz_total_cases_cnt}"
                )
                fuzz_win.addstr(
                    2, 1, f"Tests found (last): {self.fuzz_last_cases_cnt}"
                )
                fuzz_win.addstr(
                    3, 1, f"Time fuzzing: {self.fuzz_total_time//1000}s"
                )
                # Symex info window
                sym_win_cols = curses.COLS - 1 - fuzz_cols
                sym_win = self.scr.derwin(
                    fuzz_lines, sym_win_cols, glob_lines - 1, fuzz_cols
                )
                sym_win.border(" ", " ", 0, " ", " ", " ", " ", " ")
                sym_win.addstr(
                    0,
                    (sym_win_cols - len(self.sym_win_title)) // 2,
                    self.sym_win_title,
                    curses.A_BOLD,
                )
                sym_win.addstr(
                    1, 1, f"Generated cases: {self.sym_total_inputs_solved}"
                )
                sym_win.addstr(
                    2,
                    1,
                    f"Avg. solving time: {self.sym_time_solving_average//1000}s",
                )
                sym_win.addstr(
                    3,
                    1,
                    f"Avg. constraints/case: {self.sym_path_contr_average}",
                )
                sym_win.addstr(
                    1,
                    sym_win_cols // 2,
                    f"Solver timeout at: {self.sym_curr_solver_timeout}ms ",
                )
                sym_win.addstr(
                    2,
                    sym_win_cols // 2,
                    f"Timeouts cnt: {self.sym_total_solver_timeouts}",
                )

                self.scr.refresh()
            except curses.error as e:
                pass

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
