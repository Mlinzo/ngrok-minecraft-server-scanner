import json
import typing
import os
import time
import datetime
import sys
import typing
import string

T = typing.TypeVar('T')

def read(filepath: str):
    with open(filepath, 'rt') as f: return f.read()

def write(filepath: str, content: str, mode: str ='wt'):
    with open(filepath, mode) as f: f.write(content)

def dump(filepath: str, obj: dict):
    current_date = datetime.datetime.now().strftime('%d_%m_%Y__%H_%M_%S')
    filepath = f'{current_date}_{filepath}'
    with open(filepath, 'wt') as f: json.dump(obj, f, indent=4)

def load(filepath: str) -> dict:
    if not os.path.exists(filepath): return dict()
    with open(filepath) as f: return json.load(f)

def split_on_n(lst: list[T], n: int) -> list[list[T]]:
    k, m = divmod(len(lst), n)
    return [lst[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]

def split_by_n(lst: list[T], n: int) -> list[list[T]]:
    result = [[]]
    for el in lst:
        result[-1].append(el)
        if len(result[-1]) == n:
            result.append([])
    return result

def measure_execution_time(func: typing.Callable):
    def wrapper(*args, **kwargs):
        start = time.time()
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print(f'[timer] ({current_time}) started execution')
        func(*args, **kwargs)
        elapsed = time.time() - start
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print(f'[timer] ({current_time}) finished execution')
        print(f'[timer] execution took {elapsed/60} minutes')
    return wrapper

MC_COLOR_CODES = [
    f'\u00a7{char}' for char in string.printable
]

def remove_color_codes(s: str):
    for c_code in MC_COLOR_CODES:
        if c_code in s:
            s = s.replace(c_code, '')
    return s

def ips_from_range(ip_range: str) -> list[str]:
    if '/' not in ip_range[-3:]: return []
    ip, mask = ip_range.split('/')
    ips: list[str] = []
    if mask == '24':
        ip = '.'.join(ip.split('.')[:-1])
        for i in range(1, 256):
            ips.append(f'{ip}.{i}')
    return ips

def kill_proc(pid: int = os.getpid()):
    kill_command = f'kill {pid}'
    if sys.platform.startswith('win32'):
        kill_command = f'taskkill /F /PID {pid}'
    os.system(kill_command)
