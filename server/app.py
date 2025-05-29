import json
from flask import Flask, request, render_template
from threading import Thread
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
        # extrai campos
        distance = data['distance_m']
        date_str = data['date']
        time_str = data['time']
        camera = data['camera']
        image_b64 = data['image_b64']
    except KeyError as e:
        return {'error': f'Campo ausente: {e}'}, 400

    # armazena registro
    records.append({
        'distance': distance,
        'date': date_str,
        'time': time_str,
        'camera': camera,
        'image_b64': image_b64
    })
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recebido via HTTP: {data}")
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
