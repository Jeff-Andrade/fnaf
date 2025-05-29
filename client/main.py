import os
import time
import json
import base64
import serial
import RPi.GPIO as GPIO
import cv2
from datetime import datetime
from io import BytesIO
from RPLCD.i2c import CharLCD
from PIL import Image

# === Config SERIAL USB-C ===
SERIAL_PORT = '/dev/ttyGS0'   # Ajuste conforme seu setup
BAUDRATE = 115200
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)

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
BUZZER = 33  # (pino do pwm lmao)

# Setup GPIO
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

# Inicializar PWM no buzzer com frequência inicial 1kHz
buzzer_pwm = GPIO.PWM(BUZZER, 1000)
buzzer_pwm.stop()

# Estado inicial
current_zone = -1
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
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance_cm = (pulse_duration * 34300) / 2
    return round(distance_cm / 100, 2)  # retorna em metros

# Função de capturar foto e retornar bytes JPEG
def capture_image_bytes(size=256):
    camera = cv2.VideoCapture(0)
    time.sleep(0.5)
    ret, frame = camera.read()
    camera.release()
    if not ret:
        raise RuntimeError("Falha ao capturar imagem.")
    # Converte BGR para RGB e de numpy para PIL
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    # Crop central para quadrado
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

# Função para enviar dados via serial
def send_serial(distance, image_bytes, camera_id="1"):
    now = datetime.now()
    payload = {
        "distance_m": distance,
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M:%S"),
        "camera": camera_id,
        "image_b64": base64.b64encode(image_bytes).decode('ascii')
    }
    line = json.dumps(payload)
    ser.write(line.encode('utf-8') + b"\n")

try:
    while True:
        distance = get_distance()
        # Lógica de zona
        if distance <= 0.30:
            current_zone = 0
        elif distance < 0.60:
            current_zone = 1
        else:
            current_zone = 2

        if current_zone != last_zone:
            zone_start_time = time.time()
            last_zone = current_zone

        if (time.time() - zone_start_time) >= 0.1:
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
                # Captura e envia dados
                img_bytes = capture_image_bytes()
                send_serial(distance, img_bytes)
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
    ser.close()
