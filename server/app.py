import serial
import json
from flask import Flask, render_template
from threading import Thread
from datetime import datetime

app = Flask(__name__)

records = []

# === Configurar porta serial USB-C ===
SERIAL_PORT = '/dev/ttyACM0'   # ou '/dev/ttyGS0' ou '/dev/ttyUSB0'
BAUDRATE = 115200
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)

# === Thread para ler dados do serial ===
def read_serial():
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                data = json.loads(line)
                print(f" Recebido: {data}")
                records.append(data)
        except Exception as e:
            print(f" Erro na leitura serial: {e}")

@app.route('/')
def index():
    return render_template('index.html', records=records)

if __name__ == '__main__':
    t = Thread(target=read_serial, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)
