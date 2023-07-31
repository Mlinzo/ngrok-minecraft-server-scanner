import threading
import typing
from utils import split_on_n
from copy import deepcopy
import time
from config import THREADS_NOTIFY_PERIOD, THREADS, threads_logger
from db.controller import DBPool

class Thread(threading.Thread):
    def __init__(
            self, threadID: int, 
            funcs: list[typing.Callable[..., typing.Any]], 
            threaded_result: dict[int, list[typing.Any]],
            threaded_progress: dict[int, int],
            monitor_progress = True,
            **kwargs
        ):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.funcs = funcs
        self.completed_funcs = []
        self.monitor_progress = monitor_progress
        self.kwargs = kwargs
        self.threaded_result = threaded_result
        self.threaded_progress = threaded_progress
        if monitor_progress:
            threaded_progress[self.threadID] = 0
            threaded_result[self.threadID] = []

    def run(self):
        for i, func in enumerate(self.funcs, start=1):
            result = func(**self.kwargs)
            if self.monitor_progress:
                self.completed_funcs.append(func)
                self.threaded_progress[self.threadID] = len(self.completed_funcs)
                if result:
                    self.threaded_result[self.threadID].append(result)

def watch_progress(total_functions: int, threaded_progress: dict[int, int]):
    while True:
        time.sleep(THREADS_NOTIFY_PERIOD)
        completed_functions = sum(threaded_progress.values())
        print(f'[threads] completed {completed_functions:_} / {total_functions:_} function calls')
        if completed_functions >= total_functions:
            break
    threaded_progress = dict()

def run_threaded(
        funcs: list[typing.Callable[..., typing.Any]],
        thread_count: int,
        pool: DBPool | None = None,
    ):
    threaded_result: dict[int, list[typing.Any]]= dict()
    threaded_progress: dict[int, int] = dict()
    splitted_funcs = split_on_n(funcs, thread_count)
    funcs_count = sum([len(funcs) for funcs in splitted_funcs])
    if funcs_count < thread_count:
        thread_count = funcs_count
    pool_thread: Thread | None = None
    if pool:
        pool_thread = Thread(-2, [craft_function(pool.release_pool_loop)], threaded_result, threaded_progress, monitor_progress=False)
    if pool_thread:
        pool_thread.start()
    threads: list[Thread] = []
    for i, _funcs in enumerate(splitted_funcs):
        threads.append(Thread(i, _funcs, threaded_result, threaded_progress, pool=pool))
    threads.append(Thread(-1, [craft_function(watch_progress, len(funcs), threaded_progress)], threaded_result, threaded_progress, monitor_progress=False))
    print(f'[threads] booting up {thread_count}+2 threads...')
    [t.start() for t in threads]
    [t.join() for t in threads]
    if pool and pool_thread:
        pool.stop()
        threads_logger.info('waiting for last pool release...')
        pool_thread.join()
    result = deepcopy(threaded_result)
    threaded_result = dict()
    return extract_threads_result(result)

def extract_threads_result(threads_result: dict[int, list[typing.Any]]):
    res = []
    for thread_results in threads_result.values():
        for server_info in thread_results:
            res.append(server_info)
    return res

def craft_function(func: typing.Callable[..., typing.Any], *args, **kwargs: dict[str, typing.Any]):
    def invoke(**inv_kwargs: dict[str, typing.Any]):
        inv_kwargs = {**kwargs, **inv_kwargs}
        return func(*args, **inv_kwargs)
    return invoke

