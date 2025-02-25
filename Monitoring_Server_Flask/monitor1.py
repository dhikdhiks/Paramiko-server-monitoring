from flask import Flask, jsonify, render_template, request, Response
import paramiko
import time 

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
    return render_template('monitor1.html')

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
@app.route('/ssh-command', methods=['POST'])
def ssh_command():
    data = request.json
    host = data.get('host')
    port = int(data.get('port', 22))
    username = data.get('username')
    password = data.get('password')
    command = data.get('command')

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, password=password)

        # Stream output secara real-time
        def generate():
            stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
            for line in iter(stdout.readline, ""):
                yield line
            ssh.close()

        return Response(generate(), mimetype='text/plain')

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
