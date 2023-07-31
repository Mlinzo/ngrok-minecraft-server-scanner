# ngrok minecraft server scanner
## Installation
### Linux
```console
git clone https://github.com/Mlinzo/ngrok_minecraft_server_scanner
cd ngrok_minecraft_server_scanner
python -m venv venv
source ./venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows
```console
git clone https://github.com/Mlinzo/ngrok_minecraft_server_scanner
cd ngrok_minecraft_server_scanner
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Usage
### Help
```console
python main.py -h
usage: main.py [-h] [-g [GEN_SOCKETS]] [-d [DB_SOCKETS]] [-p [PRE_LOAD_SOCKETS]] [-t THREADS] [-l LOAD] [-o OUTPUT] [-tm TIMEOUT]

OPTIONS:
  -h, --help            show this help message and exit
  -g [GEN_SOCKETS], --gen_sockets [GEN_SOCKETS]
                        Generate host:port for ngrok.io automatically
  -d [DB_SOCKETS], --db_sockets [DB_SOCKETS]
                        Take host:port from database where status set to null
  -p [PRE_LOAD_SOCKETS], --pre_load_sockets [PRE_LOAD_SOCKETS]
                        Generate host:port for ngrok.io automatically and load it to db with status is set to null
  -t THREADS, --threads THREADS
                        Number of threads to use for scanning (default - 2048)
  -l LOAD, --load LOAD  Load host:port from txt file
  -o OUTPUT, --output OUTPUT
                        Output result to txt file
  -tm TIMEOUT, --timeout TIMEOUT
                        Timeout in seconds for socket response (default - 10)

Example: python .\main.py --gen_sockets to generate ngrok host:port and start a scanner
```
### How to scan all ports on 0.tcp.eu.ngrok.io - 9.tcp.eu.ngrok.io
Generate all possible host:port combinations and load to db with NULL status
```console
python main.py --pre_load_sockets
```
After all sockets have been loaded you can now run it like this to scan all host:port from database with NULL status
```console
python main.py --db_sockets
```
