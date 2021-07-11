import _thread
import time
import traceback


class Future:

    def __init__(self, callback=None):
        self._val = None
        self._done = False

        self._callback = callback

    def __repr__(self):
        return "{}({}, done={})".format(type(self).__name__, self._val, self._done)

    def set_val(self, val) -> 'Future':
        self._val = val
        self._done = True
        if self._callback is not None:
            self._callback(val)
        return self

    def is_done(self):
        return self._done

    def get_val(self):
        return self._val

    def wait(self, poll_rate_secs=0.1, time_limit_secs=None):
        if self._done:
            return self._val
        else:
            start_time_secs = time.time()
            while not self._done:
                cur_time_secs = time.time()
                if time_limit_secs is not None and cur_time_secs - start_time_secs > time_limit_secs:
                    raise ValueError("Future did not complete within time limit ({} sec)".format(time_limit_secs))
                time.sleep(poll_rate_secs)
            return self._val


def do_work_on_background_thread(runnable, future=None) -> Future:
    """
    runnable: () -> val or () -> None
    future: an optional Future to use. If None, a new one will be made.
    """
    if future is None:
        future = Future()

    def _do_work():
        result = None
        try:
            result = runnable()
        except Exception:
            traceback.print_exc()
        future.set_val(result)

    _thread.start_new_thread(_do_work, ())
    return future


def prompt_for_text(window_title, question_text, default_text, do_async=True) -> Future:
    try:
        import tkinter as tk
    except ImportError:
        traceback.print_exc()
        print("ERROR: Couldn't import tkinter, returning None, hope this wasn't important...")
        return Future().set_val(None)

    def _do_prompt():
        window = tk.Tk()
        window.title(window_title)

        greeting = tk.Label(text=question_text, anchor="w")
        greeting.pack(fill="both")

        text_box = tk.Text()
        text_box.insert("1.0", default_text)
        text_box.pack()

        result = [None]

        def confirm():
            result[0] = text_box.get("1.0", tk.END)
            window.destroy()

        ok_btn = tk.Button(master=window, text="Ok", command=confirm)
        ok_btn.pack()

        window.mainloop()

        return result[0]

    if do_async:
        return do_work_on_background_thread(_do_prompt)
    else:
        res = Future()
        res.set_val(_do_prompt())
        return res


if __name__ == "__main__":
    # fut = prompt_for_text("test title", "Give some text please:", "default text")
    # print(fut.wait())

    def do_some_long_running_work():
        sum = 0
        for i in range(1, 100000):
            for j in range(1, 1000):
                if i % j == 0:
                    sum += 1
        return sum

    fut = do_work_on_background_thread(do_some_long_running_work)
    while not fut.is_done():
        print("waiting on main thread...")
        time.sleep(0.1)
    print(fut.get_val())