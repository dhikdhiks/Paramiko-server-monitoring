from flask import Flask, jsonify, render_template, request, Response
import paramiko
import time
import subprocess
import os

app = Flask(__name__)

# Fungsi untuk mengambil data monitoring
def get_server_stats(host, port, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, password=password)

        # CPU Usage
        stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        cpu_usage = stdout.read().decode().strip()

        # Memory Usage
        stdin, stdout, stderr = ssh.exec_command("free -m | awk 'NR==2{printf \"%s %s\", $3, $2}'")
        mem_info = stdout.read().decode().strip().split()
        mem_used, mem_total = int(mem_info[0]), int(mem_info[1])
        mem_usage_percent = (mem_used / mem_total) * 100

        # Disk Space
        stdin, stdout, stderr = ssh.exec_command("df -h / | awk 'NR==2{printf \"%s/%s (%s)\", $3,$2,$5}'")
        disk_space = stdout.read().decode().strip()

        # Uptime
        stdin, stdout, stderr = ssh.exec_command("uptime -p")
        uptime = stdout.read().decode().strip()

        ssh.close()
        return float(cpu_usage), mem_usage_percent, disk_space, uptime
    except Exception as e:
        return None, None, None, f"Error: {str(e)}"

# Endpoint untuk halaman utama
@app.route('/')
def index():
    return render_template('monitor-rmk.html')

# Endpoint untuk monitoring
@app.route('/monitor', methods=['POST'])
def monitor():
    data = request.json
    host = data.get('host')
    port = int(data.get('port', 22))
    username = data.get('username')
    password = data.get('password')

    cpu, mem_usage, disk_space, uptime = get_server_stats(host, port, username, password)
    return jsonify({
        'cpu_usage': cpu,
        'memory_usage': mem_usage,
        'disk_space': disk_space,
        'uptime': uptime
    })


# Endpoint untuk menjalankan perintah SSH
def start_shellinabox():
    # Start ShellInABox on port 4200
    subprocess.Popen(['shellinaboxd', 
                     '-t', 
                     '--no-beep',
                     '--disable-ssl',
                     '-p', '4200',
                     '-s', '/:SSH:22:localhost'])

if __name__ == '__main__':
    app.run(host='10.201.0.228', port=5000, debug=True)
