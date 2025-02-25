from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import psutil
import subprocess
import threading
import paramiko
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Fungsi untuk mendapatkan informasi sistem
def get_system_info():
    disk_usage = psutil.disk_usage('/')
    memory_info = psutil.virtual_memory()
    cpu_usage = psutil.cpu_percent(interval=1)
    uptime = subprocess.check_output("uptime -p", shell=True).decode().strip()
    
    return {
        "disk_usage": disk_usage.percent,
        "memory_usage": memory_info.percent,
        "cpu_usage": cpu_usage,
        "uptime": uptime
    }

# Route utama untuk halaman web
@app.route('/')
def index():
    return render_template('index.html')

# API untuk mendapatkan informasi sistem
@app.route('/api/system-info')
def system_info():
    return jsonify(get_system_info())

# WebSocket untuk pembaruan real-time
@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('get_system_info')
def send_system_info():
    while True:
        info = get_system_info()
        emit('system_info', info)
        socketio.sleep(2)

# SSH Terminal
ssh_clients = {}

@socketio.on('ssh_connect')
def ssh_connect(data):
    ip = data['ip']
    username = data['username']
    password = data['password']
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password)
        ssh_clients[request.sid] = client
        
        # Membuka shell interaktif
        channel = client.invoke_shell()
        def read_channel():
            while True:
                if channel.recv_ready():
                    output = channel.recv(1024).decode()
                    emit('ssh_output', {'output': output})
                socketio.sleep(0.1)
        
        threading.Thread(target=read_channel).start()
        emit('ssh_status', {'status': 'connected'})
    except Exception as e:
        emit('ssh_status', {'status': 'failed', 'error': str(e)})

@socketio.on('ssh_input')
def ssh_input(data):
    client = ssh_clients.get(request.sid)
    if client:
        channel = client.invoke_shell()
        channel.send(data['input'] + '\n')

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in ssh_clients:
        ssh_clients[request.sid].close()
        del ssh_clients[request.sid]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)