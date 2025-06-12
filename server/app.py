import base64
from io import BytesIO
from PIL import Image
from flask import Flask, request, render_template
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
        distance   = data['distance_m']
        date_str   = data['date']
        time_str   = data['time']
        camera     = data['camera']
        image_b64  = data['image_b64']
    except KeyError as e:
        return {'error': f'Campo ausente: {e}'}, 400

    # 1) Decodifica base64 para bytes
    try:
        img_data = base64.b64decode(image_b64)
        img = Image.open(BytesIO(img_data))
    except Exception as e:
        return {'error': f'Erro ao decodificar imagem: {e}'}, 400

    # 2) Redimensiona para 320×240 (QVGA)
    img = img.resize((320, 240))

    # 3) Re-encoda para JPEG base64
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    resized_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Extrai infos do cliente
    client_ip  = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'desconhecido')

    # Armazena o registro com a imagem redimensionada
    records.append({
        'distance':     distance,
        'date':         date_str,
        'time':         time_str,
        'camera':       camera,
        'image_b64':    resized_b64,
        'received_at':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'client_ip':    client_ip,
        'user_agent':   user_agent
    })

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recebido de {client_ip} – {user_agent}: "
          f"Cam={camera}, Dist={distance}cm")
    return {'status': 'ok'}, 200


@app.route('/logs', methods=['GET'])
def logs():
    # Exibe os registros detalhados
    return render_template('logs.html', records=records)

# Para execução direta em dev
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
