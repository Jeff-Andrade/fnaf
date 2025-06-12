import base64
from io import BytesIO
from PIL import Image
from flask import Flask, request, render_template, jsonify
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
        distance  = data['distance_m']
        date_str  = data['date']
        time_str  = data['time']
        camera    = data['camera']
        image_b64 = data['image_b64']
    except KeyError as e:
        return {'error': f'Campo ausente: {e}'}, 400

    # decodifica & redimensiona
    try:
        img = Image.open(BytesIO(base64.b64decode(image_b64)))
        img = img.resize((320, 240))
        buf = BytesIO()
        img.save(buf, format='JPEG')
        resized_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        return {'error': f'Erro ao processar imagem: {e}'}, 400

    client_ip  = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'desconhecido')
    record = {
        'distance':     distance,
        'date':         date_str,
        'time':         time_str,
        'camera':       camera,
        'image_b64':    resized_b64,
        'received_at':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'client_ip':    client_ip,
        'user_agent':   user_agent
    }
    records.append(record)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recebido de {client_ip}: Cam={camera}, Dist={distance}cm")
    return {'status': 'ok'}, 200

# rota que expõe JSON com todos os registros
@app.route('/api/records', methods=['GET'])
def api_records():
    return jsonify(records)

@app.route('/logs', methods=['GET'])
def logs():
    return render_template('logs.html', records=records)

# rota que expõe JSON com todos os logs (mesmos dados)
@app.route('/api/logs', methods=['GET'])
def api_logs():
    return jsonify(records)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
