from .engine import session_factory, scoped_session
from .models import StatusDB, SocketDB, HostDB, MServerDB, BaseDB, create_all
from ..schemas import Status, Socket, Host, MServer, Base as BaseModel
from config import db_logger
from config import DB_POOL_RELEASE_PERIOD, DB_PATH
from threading import Lock
from utils import read, load, split_by_n, write
import typing
import time

class DBBaseController():
    def __init__(self):
        self.Session = scoped_session(session_factory)
        self._conn = self.Session()
        create_all()
        self._init_sql()
        self.MINECRAFT_SERVER_STATUS: Status = [stat for stat in self.get_statuses() if stat.name == 'Minecraft Server'][0]

    def __del__(self):
        self.Session.remove()
        db_logger.info('connection closed')

    def _init_sql(self):
        status = Status(name='Minecraft Server')
        self.safe_add_all_statuses([status])

    def get_statuses(self, status_in: list[str] = [], limit: int | None = None):
        q = self._conn.query(StatusDB)
        if status_in:
            q = q.filter(StatusDB.name.in_(status_in))
        if limit is not None:
            q = q.limit(limit)
        res = q.all()
        return [Status.from_orm(rec) for rec in res]

    def get_hosts(self, hostname_in: list[str] = [], limit: int | None = None):
        q = self._conn.query(HostDB)
        if hostname_in:
            q = q.filter(HostDB.name.in_(hostname_in))
        if limit is not None:
            q = q.limit(limit)
        res = q.all()
        return [ Host.from_orm(rec) for rec in res ]

    def get_sockets(self, host_id_in: list[int] = [], port_in: list[int] = [], limit: int | None = None):
        q = self._conn.query(SocketDB)
        if len(host_id_in) != len(port_in):
            host_id_in = []
            port_in = []
        if host_id_in and port_in:
            q = q.filter(SocketDB.hostId.in_(host_id_in)).filter(SocketDB.port.in_(port_in))
        if limit is not None:
            q = q.limit(limit)
        res = q.all()
        return [ Socket.from_orm(rec) for rec in res ]

    def get_servers(self, socket_id_in: list[int] = [], limit: int | None = None):
        q = self._conn.query(MServerDB)
        if socket_id_in:
            q = q.filter(MServerDB.socketId.in_(socket_id_in))
        if limit is not None:
            q = q.limit(limit)
        res = q.all()
        return [ MServer.from_orm(rec) for rec in res ]

    def get(self, DB_type: typing.Type[BaseDB], id: int):
        return self._conn.get(DB_type, id)

    def update(self, model: BaseModel, commit = False):
        return model.update_db(self, commit=commit)

    def add_all(self, entities: list[BaseModel], in_place=True, no_output=False, commit=True) -> list[BaseModel]:
        if not entities: return []
        Entity_type = type(entities[0])
        entities_db: list[BaseDB] = [ent.to_db() for ent in entities]
        self._conn.add_all(entities_db)
        if not commit:
            return []
        self._conn.commit()
        if no_output: return []
        if in_place:
            for ent, ent_db in zip(entities, entities_db):
                ent.id = ent_db.id #type: ignore
            return []
        return [Entity_type.from_orm(rec) for rec in entities_db]

    def safe_add_all_hosts(self, hosts: list[Host]):
        hosts_to_add: list[Host] = []
        hostnames: list[str] = [h.name for h in hosts]
        hosts_from_db = self.get_hosts(hostname_in=hostnames, limit=len(hostnames))
        hosts_map = { host.name: host for host in hosts_from_db }
        for host in hosts:
            if host.name in hosts_map:
                host.id = hosts_map[host.name].id
                continue
            if host.name in [h.name for h in hosts_to_add]:
                continue
            hosts_to_add.append(host)
        self.add_all(hosts_to_add) #type: ignore
        hosts_map = { host.name: host.id for host in hosts if host.id > 0 }
        for host in hosts:
            host.id = hosts_map[host.name]
        return len(hosts_to_add)
    
    def safe_add_all_sockets(self, sockets: list[Socket], notify=False, commit=False):
        sockets_splitted = split_by_n(sockets, 333) # slqlite has parameter limit of 999
        new_hosts_c = 0
        total_socks_to_add = 0
        total_to_load = len(sockets)
        total_passed = 0
        for sockets in sockets_splitted:
            socks_to_add: list[Socket] = []
            hosts: list[Host] = [s.host for s in sockets]
            new_hosts_c += self.safe_add_all_hosts(hosts)
            host_ids: list[int] = [h.id for h in hosts]
            ports: list[int] = [s.port for s in sockets]
            socks_from_db = self.get_sockets(host_id_in=host_ids, port_in=ports, limit=len(host_ids)*len(ports))
            socks_map = { (sock.host.id, sock.port): sock for sock in socks_from_db }        
            for sock in sockets:
                socks_map_key = (sock.host.id, sock.port)
                if socks_map_key in socks_map:
                    sock.id = socks_map[socks_map_key].id
                    continue
                if socks_map_key in [(s.host.id, s.port) for s in socks_to_add]:
                    continue
                socks_to_add.append(sock)
            self.add_all(socks_to_add, commit=commit) #type: ignore
            if notify and total_passed % 50_000 < 333 and total_passed > 50_000:
                db_logger.info(f'{total_passed:_} / {total_to_load:_} sockets added to db')
            total_socks_to_add += len(socks_to_add)
            total_passed += len(sockets)
        if not commit:
            self._conn.commit()
        return (new_hosts_c, total_socks_to_add)

    def safe_add_all_servers(self, servers: list[MServer], output_to: str = ''):
        servers_to_add: list[MServer] = []
        socks: list[Socket] = [s.socket for s in servers]
        new_ips_c, new_socks_c = self.safe_add_all_sockets(socks)
        servers_from_db = self.get_servers(socket_id_in=[s.id for s in socks], limit=len(socks))
        servers_map = { s.socket.id: s for s in servers_from_db }
        for server in servers:
            if server.socket.id in servers_map:
                server.id = servers_map[server.socket.id].id
                continue
            if server.socket.id in [s.socket.id for s in servers_to_add]:
                continue
            servers_to_add.append(server)
        self.add_all(servers_to_add) #type: ignore
        if output_to and len(servers) > 0:
            write(output_to, '\n'.join([s.printable for s in servers])+'\n' ,'at')
            db_logger.info(f'dumped found servers to {output_to}')
        return (new_ips_c, new_socks_c, len(servers_to_add))

    def safe_add_all_statuses(self, statuses: list[Status]):
        to_add: list[Status] = []
        from_db = self.get_statuses(status_in=[stat.name for stat in statuses], limit=len(statuses))
        mapping = { x.name: x for x in from_db }
        for a in statuses:
            if a.name in mapping:
                a.id = mapping[a.name].id
                continue
            if a.name in [x.name for x in to_add]:
                continue
            db_logger.info(f'new status: {a.name}')
            to_add.append(a)
        self.add_all(to_add) #type: ignore
        return len(to_add)

    def safe_update_all_sockets(self, sockets: list[Socket]):
        statuses = [socket.status for socket in sockets]
        new_statuses_c = self.safe_add_all_statuses([stat for stat in statuses if stat])
        non_db_sockets = [socket for socket in sockets if socket.id == 0]
        if non_db_sockets:
            self.safe_add_all_sockets(non_db_sockets)
        for sock in sockets:
            sock.update_db(self, commit=False)
        self._conn.commit()
        return new_statuses_c

class DBController(DBBaseController):
    def __init__(self):
        DBBaseController.__init__(self)

    def add_status(self, status: Status):
        status_db = status.to_db()
        self._conn.add(status_db)
        self._conn.commit()
        return Status.from_orm(status_db)

    def add_server(self, server: MServer):
        server_db = server.to_db()
        self._conn.add(server_db)
        self._conn.commit()
        return MServer.from_orm(server_db)

    def get_target_sockets(self):
        res = self._conn.query(SocketDB).filter(SocketDB.statusId == None).all()
        if len(res) == 0:
            db_logger.info(f'[warning] no target hosts was found in database. if it is your first launch, run it with --gen_sockets, otherwise consider adjusting database file {DB_PATH}')
        return [Socket.from_orm(rec) for rec in res]

    def load_sockets_txt(self, filepath: str):
        db_logger.info(f'loading sockets from {filepath}')
        if not filepath.endswith('.txt'):
            raise Exception(f'Non txt file specified for sockets load!')
        lines = list(set(read(filepath).split()))
        sockets = [Socket(host=Host(name=line.split(':')[0]), port=int(line.split(':')[-1])) for line in lines]
        new_sockets = self.safe_add_all_sockets(sockets)
        db_logger.info(f'{new_sockets} hosts loaded to database')
        return sockets

    def load_servers_json(self, filepath: str):
        db_logger.info(f'loading servers from {filepath}')
        if not filepath.endswith('.json'):
            return db_logger.info(f'Non json file specified for servers load!')
        data = load(filepath)
        servers_from_file: list[MServer] = []
        for record in data:
            if any([key not in ['connect', 'connection', 'max_players', 'version', 'description'] for key in record]): continue
            socket_key = 'connect' if 'connect' in record else 'connection'
            socket_rec = record[socket_key].split(':')
            socket = Socket(host=Host(name=socket_rec[0]), port=int(socket_rec[1]), status=self.MINECRAFT_SERVER_STATUS)
            server = MServer(
                socket=socket,
                version=record['version'],
                description=record['description'],
                max_players=int(record['max_players'])
            )
            servers_from_file.append(server)
        new_servers = self.safe_add_all_servers(servers_from_file)
        db_logger.info(f'{new_servers} servers loaded to database')

    def load_ngrok_sockets(self):
        db_logger.info('loading ngrok host:port to database. this may take some time...')
        sockets = [Socket(host=Host(name=f'{i}.tcp.eu.ngrok.io'), port=p) for i in range(10) for p in range(1, 65536)]
        new_hosts, new_sockets = self.safe_add_all_sockets(sockets, notify=True)
        if new_hosts > 0: db_logger.info(f'{new_hosts} hosts added')
        if new_sockets > 0: db_logger.info(f'{new_sockets} sockets added')
        db_logger.info('ngrok host:port loaded to database')

class DBPool(DBBaseController):
    def __init__(self, output_path: str = ''):
        DBBaseController.__init__(self)
        self._servers_add: list[MServer] = []
        self._sockets_update: list[Socket] = []
        self._sockets_add: list[Socket] = []
        self._stop_loop = False
        self._output_path = output_path
        if output_path and not output_path.endswith('.txt'):
            raise Exception('Non txt file for output specified!')
        db_logger.info('pool init')

    def stop(self):
        self._stop_loop = True

    def add_server(self, server: MServer):
        with Lock():
            self._servers_add.append(server)
            self._sockets_update.append(server.socket)

    def update_socket(self, socket: Socket):
        with Lock():
            self._sockets_update.append(socket)

    def add_socket(self, socket: Socket):
        with Lock():
            self._sockets_add.append(socket)

    def release_pool_loop(self):
        db_logger.info('started pool loop')
        while not self._stop_loop:
            time.sleep(DB_POOL_RELEASE_PERIOD)
            db_logger.info(f'releasing pool...')

            with Lock():
                servers_add = [*self._servers_add]
                self._servers_add = []
                sockets_upd = [*self._sockets_update]
                self._sockets_update = []
                sockets_add = [*self._sockets_add]
                self._sockets_add = []                

            new_statuses = 0
            new_hosts = 0
            new_servers = 0
            new_sockets = 0
            
            new_statuses_c = self.safe_update_all_sockets(sockets_upd)
            new_statuses += new_statuses_c

            new_hosts_c, new_sockets_c = self.safe_add_all_sockets(sockets_add)
            new_hosts += new_hosts_c
            new_sockets += new_sockets_c

            new_hosts_c, new_sockets_c, new_servers_c = self.safe_add_all_servers(servers_add, self._output_path)
            new_hosts += new_hosts_c
            new_sockets += new_sockets_c
            new_servers += new_servers_c

            db_logger.info(f'pool released')
            if new_statuses > 0: db_logger.info(f'{new_statuses} statuses added')
            if len(sockets_upd) > 0: db_logger.info(f'{len(sockets_upd)} sockets updated')
            if new_sockets > 0: db_logger.info(f'{new_sockets} sockets added')
            if new_hosts > 0: db_logger.info(f'{new_hosts} hosts added')
            if new_servers > 0: db_logger.info(f'{new_servers} servers added')

