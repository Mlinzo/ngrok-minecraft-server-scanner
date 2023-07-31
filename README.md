# ngrok minecraft server scanner
## Installation
### Linux
```bash
git clone https://github.com/Mlinzo/ngrok_minecraft_server_scanner
cd ngrok_minecraft_server_scanner
python -m venv venv
source ./venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows
```bash
git clone https://github.com/Mlinzo/ngrok_minecraft_server_scanner
cd ngrok_minecraft_server_scanner
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Usage
### Help
```bash
python main.py -h
```
### How to scan all ports on 0.tcp.eu.ngrok.io - 9.tcp.ngrok.io
Generate all possible host:port combinations and load to db with NULL status
```bash
python main.py --pre_load_sockets
```
After all sockets have been loaded you can now run it like this to scan all host:port from database with NULL status
```bash
python main.py --db_sockets
```
