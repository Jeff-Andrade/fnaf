import json
from flask import Flask, request, render_template, redirect, url_for
from datetime import datetime

app = Flask(__name__)

records = []

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', records=records)

@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    if not data:
        return {'error': 'JSON inválido ou ausente'}, 400
    try:
        distance = data['distance_m']
        date_str = data['date']
        time_str = data['time']
        camera = data['camera']
        image_b64 = data['image_b64']
    except KeyError as e:
        return {'error': f'Campo ausente: {e}'}, 400

    # Extrai infos do cliente
    client_ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'desconhecido')

    # Armazena tudo num único registro
    records.append({
        'distance': distance,
        'date': date_str,
        'time': time_str,
        'camera': camera,
        'image_b64': image_b64,
        'received_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'client_ip': client_ip,
        'user_agent': user_agent
    })

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recebido de {client_ip} – {user_agent}: {data}")
    return {'status': 'ok'}, 200

@app.route('/logs', methods=['GET'])
def logs():
    # Exibe os registros detalhados
    return render_template('logs.html', records=records)

# Para execução direta em dev
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
