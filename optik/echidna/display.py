import curses
import threading
from time import sleep
from datetime import datetime


def generate_progress_bar(bar_len: int, current: int, _max: int) -> str:
    fill_char = "\u2588"
    res = "|"
    fill_ratio = current / _max
    filled_bar = fill_char * int((bar_len - 2) * fill_ratio)
    res += filled_bar
    res += " " * (bar_len - 1 - len(res))
    res += "|"
    res += f" {current:3}/{_max}"
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
        self.current_task_line_1 = ""
        self.current_task_line_2: Union[Tuple[int, int], str] = "Starting up..."
        self.current_task_line_3 = ""
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
        self.sym_solver_timeout: Optional[int] = None
        self.sym_time_solving_average = 0  # in ms
        self.sym_time_solving_total = 0  # in ms
        self.sym_path_constr_average = 0
        self._sym_path_constr_cnt = 0
        self._sym_solving_cnt = 0
        self.res_win_title = "Results"
        self.res_cases: List[List[str]] = []
        # WINDOW SIZES
        self.global_win_x_ratio = 0.3
        self.global_win_y_lines = 3
        self.fuzz_win_x_ratio = 0.3
        self.fuzz_win_y_lines = 4
        # OTHER
        self._show_echidna_timer = False

    def reset_current_task(self):
        self.current_task_line_1 = ""
        self.current_task_line_2 = ""
        self.current_task_line_3 = ""

    def start_echidna_task_timer(self):
        self.reset_current_task()
        self._start_time = datetime.now()
        self._show_echidna_timer = True

    def stop_echidna_task_timer(self):
        self._show_echidna_timer = False
        self.reset_current_task()

    def _get_elapsed_time_s(self):
        return int((datetime.now() - self._start_time).total_seconds())

    def update_echidna_task_timer(self):
        self.current_task_line_2 = (
            f"Running echidna campaign... {self._get_elapsed_time_s()} s"
        )

    def update_avg_path_constraints(self, nb_constraints: int) -> None:
        self.sym_path_constr_average = (
            self.sym_path_constr_average * self._sym_path_constr_cnt
            + nb_constraints
        ) // (self._sym_path_constr_cnt + 1)
        self._sym_path_constr_cnt += 1

    def update_solving_time(self, ms: int) -> None:
        self.sym_time_solving_total += ms
        self.sym_time_solving_average = (
            self.sym_time_solving_average * self._sym_solving_cnt + ms
        ) // (self._sym_solving_cnt + 1)
        self._sym_solving_cnt += 1

    def start(self, scr):
        self.active = True
        self.scr = scr

    @staticmethod
    def add_info(w, y: int, x: int, what: str, info, info_col=None) -> None:
        what += ":"
        w.addstr(y, x, what, BLUE)
        if info_col is None:
            w.addstr(f" {info}")
        else:
            w.addstr(f" {info}", info_col)

    def update(self):
        if self.active:
            if self._show_echidna_timer:
                self.update_echidna_task_timer()
            try:
                self.scr.erase()
                # Print border
                self.scr.border(0)
                # Write main title
                self.scr.addstr(
                    0,
                    curses.COLS // 2 - len(self.main_title) // 2,
                    self.main_title,
                    curses.A_BOLD | GREEN,
                )
                # Global info window
                global_win = self.scr.derwin(
                    self.global_win_y_lines * 2 - 1,
                    int(curses.COLS * self.global_win_x_ratio),
                    0,
                    1,
                )
                self.add_info(
                    global_win, 1, 1, "Iteration", f"#{self.iteration}"
                )
                self.add_info(global_win, 2, 1, "Mode", self.mode)
                self.add_info(global_win, 3, 1, "Corpus size", self.corpus_size)
                # Current info window
                glob_lines, glob_cols = global_win.getmaxyx()
                current_win = self.scr.derwin(
                    glob_lines, curses.COLS - 1 - glob_cols, 0, glob_cols
                )
                current_win.addstr(
                    1,
                    (current_win.getmaxyx()[1] - len(self.current_task_line_1))
                    // 2,
                    self.current_task_line_1,
                )
                if isinstance(self.current_task_line_2, tuple):
                    line2 = generate_progress_bar(
                        40,  # TODO adapt len to window size
                        *self.current_task_line_2,
                    )
                else:
                    line2 = self.current_task_line_2
                current_win.addstr(
                    2,
                    (current_win.getmaxyx()[1] - len(line2)) // 2,
                    line2,
                )
                current_win.addstr(
                    3,
                    (current_win.getmaxyx()[1] - len(self.current_task_line_3))
                    // 2,
                    self.current_task_line_3,
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
                    curses.A_BOLD | GREEN,
                )
                self.add_info(
                    fuzz_win,
                    1,
                    1,
                    "Tests found (total)",
                    self.fuzz_total_cases_cnt,
                )
                self.add_info(
                    fuzz_win,
                    2,
                    1,
                    "Tests found (last)",
                    self.fuzz_last_cases_cnt,
                )
                self.add_info(
                    fuzz_win,
                    3,
                    1,
                    "Time fuzzing",
                    f"{self.fuzz_total_time//1000}s",
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
                    curses.A_BOLD | GREEN,
                )
                self.add_info(
                    sym_win,
                    1,
                    1,
                    "Generated cases",
                    self.sym_total_inputs_solved,
                )
                self.add_info(
                    sym_win,
                    2,
                    1,
                    "Total solving time",
                    f"{self.sym_time_solving_total//1000}s",
                )
                self.add_info(
                    sym_win,
                    3,
                    1,
                    "Avg. solving time",
                    f"{self.sym_time_solving_average}ms",
                )
                self.add_info(
                    sym_win,
                    1,
                    sym_win_cols // 2,
                    "Solver timeout",
                    (
                        f"{self.sym_solver_timeout}ms"
                        if self.sym_solver_timeout
                        else "none"
                    ),
                    YELLOW,
                )
                self.add_info(
                    sym_win,
                    2,
                    sym_win_cols // 2,
                    "Timeouts cnt",
                    self.sym_total_solver_timeouts,
                    RED if self.sym_total_solver_timeouts else None,
                )
                self.add_info(
                    sym_win,
                    3,
                    sym_win_cols // 2,
                    "Avg. constraints/case",
                    self.sym_path_constr_average,
                )
                # Results windows
                res_win_y_start = glob_lines + fuzz_lines - 3
                res_win = self.scr.derwin(
                    curses.LINES - 1 - res_win_y_start,
                    curses.COLS - 2,
                    res_win_y_start,
                    1,
                )
                res_lines, res_cols = res_win.getmaxyx()
                res_win.border(" ", " ", 0, " ", " ", " ", " ", " ")
                res_win.addstr(
                    0,
                    (res_cols - len(self.res_win_title)) // 2,
                    self.res_win_title,
                    curses.A_BOLD | GREEN,
                )
                if self.res_cases:
                    y_case_cnt = 1
                    unshown_cnt = 0
                    for j, case in enumerate(self.res_cases):
                        if y_case_cnt + len(case) + 1 >= res_lines:
                            unshown_cnt = len(self.res_cases) - j
                            break
                        case_win = res_win.derwin(
                            len(case) + 1,
                            res_cols,
                            y_case_cnt,
                            0,
                        )
                        case_win.border(" ", " ", " ", 0, " ", " ", " ", " ")
                        for i, call in enumerate(case):
                            case_win.addstr(i, 1, call, RED)
                        y_case_cnt += len(case) + 1
                    # TODO display how many assertions are not shown
                else:
                    no_cases_msg = "-"
                    res_win.addstr(
                        res_lines // 2,
                        (res_cols - len(no_cases_msg)) // 2,
                        no_cases_msg,
                    )

                self.scr.refresh()
            except curses.error as e:
                pass

    def stop(self):
        self.active = False
        self.scr = None


display = HybridEchidnaDisplay()
display_thread = None

GREEN = None
BLUE = None
YELLOW = None
RES = None


def _display():
    global display
    global GREEN
    global BLUE
    global RED
    global YELLOW
    exc = None
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.start_color()
        curses.use_default_colors()
        curses.init_color(curses.COLOR_RED, 245 * 4, 130 * 4, 0 * 4)
        curses.init_color(curses.COLOR_YELLOW, 250 * 4, 230 * 4, 10 * 4)
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_BLUE, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        GREEN = curses.color_pair(1)
        BLUE = curses.color_pair(2)
        YELLOW = curses.color_pair(3)
        RED = curses.color_pair(4)
        display.start(stdscr)
        while display.active:
            display.update()
            sleep(0.1)
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
