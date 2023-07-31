from mcstatus import JavaServer
from utils import remove_color_codes, kill_proc
from threads import run_threaded, craft_function
from config import scanner_logger
from typing import Callable
from db.controller import DBPool
from db.schemas import MServer, Status, Socket, Host
import socket
import json

KNOWN_EXCEPTIONS = (OSError, socket.timeout)

def handle_result(scan_function: Callable[[Socket, int], MServer], socket: Socket, timeout: int, pool: DBPool | None = None):
    if not pool: raise Exception('No pool provided!')
    try:
        server = scan_function(socket, timeout)
        socket.status = pool.MINECRAFT_SERVER_STATUS
        pool.add_server(server)
        return server
    except KNOWN_EXCEPTIONS as ex:
        status_name = f'{ex.__class__.__name__} {ex}'
        socket.status = Status(name=status_name)
        pool.update_socket(socket)
    except Exception as ex:
        scanner_logger.exception(f'UNKNOWN EXCEPTION {ex.__class__.__name__} {ex}')
        kill_proc()

def obtain_server_info(socket: Socket, timeout: int):
    server = JavaServer(socket.host.name, socket.port, timeout=timeout)
    status = server.status()
    description = remove_color_codes(status.description)
    raw_result = {
        'socket': socket,
        'version': status.version.name.strip(),
        'description': description.strip(),
        'max_players':status.players.max
    }
    result = MServer(**raw_result)
    raw_result['version'] = raw_result['version'][:15]
    raw_result['description'] = raw_result['description'][:25]
    raw_result['socket'] = f"{result.socket.host.name}:{result.socket.port}"
    log_result = json.dumps(raw_result)
    scanner_logger.info(f'server discovered {log_result}')
    return result

def check_ngrok_sockets_t(pool: DBPool, threads: int, timeout: int) -> list[MServer]:
    scanner_logger.info(f'scannig ngrok sockets...')
    threaded_funcs = [craft_function(handle_result, obtain_server_info, Socket(host=Host(name=f'{i}.tcp.eu.ngrok.io'), port=p), timeout) for i in range(10) for p in range(1, 65_536)]
    servers = run_threaded(threaded_funcs, thread_count=threads, pool=pool)
    scanner_logger.info(f'scanned ngrok sockets. found {len(servers):_} servers')
    return servers

def check_target_sockets_t(sockets: list[Socket], pool: DBPool, threads: int, timeout: int) -> list[MServer]:
    if not sockets:
        scanner_logger.info('no sockets to scan!')
        return []
    scanner_logger.info(f'{len(sockets):_} sockets to scan')
    threaded_funcs = [craft_function(handle_result, obtain_server_info, socket, timeout) for socket in sockets]
    servers = run_threaded(threaded_funcs, thread_count=threads, pool=pool)
    scanner_logger.info(f'scanned {len(sockets):_} sockets. found {len(servers):_} servers')
    return servers
