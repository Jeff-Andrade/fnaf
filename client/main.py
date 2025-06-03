import os
import time
import json
import base64
import requests
import RPi.GPIO as GPIO
import cv2
from datetime import datetime
from io import BytesIO
from RPLCD.i2c import CharLCD
from PIL import Image

# Configuração da API HTTP
API_URL = 'https://projeto-fnaf.onrender.com/upload'  # substitua pelo IP/URL real

# LCD via I2C
lcd = CharLCD('PCF8574', 0x27, cols=20, rows=4)

# Usar GPIO.BOARD
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Mapeamento de pinos físicos
TRIG = 19
ECHO = 21
RED = 23
GREEN = 5
BLUE = 31
BUZZER = 33  # pino do pwm

# Setup GPIO
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

# Inicializar PWM no buzzer
buzzer_pwm = GPIO.PWM(BUZZER, 1000)
buzzer_pwm.stop()

# Estado inicial\ ncurrent_zone = -1
last_zone = -1
zone_start_time = 0

lcd.clear()
lcd.cursor_pos = (0, 0)
lcd.write_string("Sensor Ativo")

# Função de medir distância
def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.02)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        start = time.time()
    while GPIO.input(ECHO) == 1:
        end = time.time()

    duration = end - start
    cm = (duration * 34300) / 2
    return round(cm, 1)

# Função de capturar foto e retornar bytes JPEG
def capture_image_bytes(size=256):
    cam = cv2.VideoCapture(0)
    time.sleep(0.5)
    ret, frame = cam.read()
    cam.release()
    if not ret:
        raise RuntimeError("Falha ao capturar imagem.")

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size))

    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

# Função para enviar dados via HTTP POST
def send_http(distance, image_bytes, camera_id="1"):
    now = datetime.now()
    payload = {
        'distance_m': distance,
        'date': now.strftime('%d/%m/%Y'),
        'time': now.strftime('%H:%M:%S'),
        'camera': camera_id,
        'image_b64': base64.b64encode(image_bytes).decode('ascii')
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=5)
        if resp.status_code == 200:
            print(" Dados enviados com sucesso!")
        else:
            print(f" Erro HTTP: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f" Exception no envio HTTP: {e}")

try:
    while True:
        distance = get_distance()
        if distance <= 0.30:
            current_zone = 0
        elif distance < 0.60:
            current_zone = 1
        else:
            current_zone = 2

        if current_zone != last_zone:
            zone_start_time = time.time()
            last_zone = current_zone

        if time.time() - zone_start_time >= 0.1:
            if current_zone == 0:
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Obj extr. proximo    ")
                GPIO.output(RED, True)
                GPIO.output(GREEN, False)
                GPIO.output(BLUE, False)
                buzzer_pwm.ChangeFrequency(100)
                buzzer_pwm.start(50)
                lcd.cursor_pos = (3, 0)
                lcd.write_string("!!!!!!!!!!!!!!!!!!!!")
                img_bytes = capture_image_bytes()
                send_http(distance, img_bytes)

            elif current_zone == 1:
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Obj aproximando     ")
                GPIO.output(RED, True)
                GPIO.output(GREEN, True)
                GPIO.output(BLUE, False)
                lcd.cursor_pos = (3, 0)
                lcd.write_string("                    ")
                for _ in range(2):
                    buzzer_pwm.ChangeFrequency(1000)
                    buzzer_pwm.start(50)
                    time.sleep(0.25)
                    buzzer_pwm.stop()
                    time.sleep(0.25)
            else:
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Sistema normal      ")
                GPIO.output(RED, False)
                GPIO.output(GREEN, False)
                GPIO.output(BLUE, True)
                buzzer_pwm.stop()
                lcd.cursor_pos = (3, 0)
                lcd.write_string("                    ")

        lcd.cursor_pos = (2, 0)
        lcd.write_string(f"Dist: {distance:.2f} m     ")
        time.sleep(0.1)

except KeyboardInterrupt:
    buzzer_pwm.stop()
    lcd.clear()
    GPIO.cleanup()
