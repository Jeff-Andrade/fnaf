# Importação das bibliotecas necessárias
import RPi.GPIO as GPIO           # Controle dos pinos GPIO do Raspberry Pi
import time                       # Temporizações (sleep, time)
from RPLCD.gpio import CharLCD    # Controle do display LCD usando GPIO
import cv2                        # Acesso à câmera via OpenCV
from datetime import datetime     # Para gerar timestamps
import base64                     # Codificação de imagem para base64
import requests                   # Enviar dados para um servidor via HTTP POST
import threading                  # Execução paralela de funções
import os                         # Comandos do sistema (como shutdown)

# Flags de controle global
desligando = False               # Indica se o sistema está em processo de desligamento
lcd_lock = threading.Lock()      # Lock para evitar que duas partes escrevam no LCD ao mesmo tempo

# Função para escrita segura no LCD com proteção contra conflitos e bug de sincronização
def escrever_lcd(linha1, linha2=""):
    with lcd_lock:
        lcd.clear()
        time.sleep(0.05)         # Aguarda o LCD processar o clear
        lcd.write_string(linha1)
        if linha2:
            lcd.cursor_pos = (1, 0)
            lcd.write_string(linha2)

# Inicialização do LCD (24x4)
lcd = CharLCD(
    numbering_mode=GPIO.BOARD,
    cols=24, rows=4,
    pin_rs=37, pin_e=33,
    pins_data=[35, 31, 24, 26]
)

# Exibe mensagem de boot
escrever_lcd("Sistema iniciando...")
print("[⏳] Aguardando inicialização completa do sistema (5s)...")
time.sleep(5)

# Mensagem de build (versão)
escrever_lcd("build 4")
time.sleep(2)
escrever_lcd("")  # Limpa o LCD após mostrar o build

# Configuração dos GPIOs
GPIO.setmode(GPIO.BOARD)       # Usa a numeração física dos pinos
GPIO.setwarnings(False)        # Desativa alertas de reuso de pinos

# Definição dos pinos utilizados
TRIG = 19      # Trigger do sensor ultrassônico
ECHO = 21      # Echo do sensor ultrassônico
RED = 23       # LED vermelho
GREEN = 13     # LED verde
BLUE = 29      # LED azul
BUZZ = 36      # Buzzer
BUTTON = 5     # Botão (também usado para religar o Pi)

# Configuração dos modos dos pinos
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)
GPIO.setup(BUZZ, GPIO.OUT)
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Thread que monitora o botão físico para desligar o sistema
def monitorar_botao():
    global desligando
    while True:
        if GPIO.input(BUTTON) == GPIO.LOW and not desligando:
            desligando = True
            escrever_lcd("Mantenha pressionado", "por 3 segundos")

            start_time = time.time()
            while GPIO.input(BUTTON) == GPIO.LOW:
                if time.time() - start_time >= 3:
                    # Se segurou por 3s, desliga o sistema com segurança
                    set_color(0, 0, 0)
                    GPIO.output(BUZZ, 0)
                    escrever_lcd("")
                    time.sleep(1)
                    os.system("sudo shutdown -h now")
                    return
                time.sleep(0.1)

            # Se soltou antes de 3s, cancela o desligamento
            escrever_lcd("Operacao cancelada")
            time.sleep(2)
            escrever_lcd("")
            desligando = False
        time.sleep(0.2)

# Inicia a thread que monitora o botão
threading.Thread(target=monitorar_botao, daemon=True).start()

# Mede a distância com o sensor ultrassônico
def medir_distancia():
    GPIO.output(TRIG, False)
    time.sleep(0.05)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)

# Define a cor do LED RGB
def set_color(r, g, b):
    GPIO.output(RED, r)
    GPIO.output(GREEN, g)
    GPIO.output(BLUE, b)

def enviar_payload(payload):
    try:
        print("[+] Enviando para https://projeto-fnaf.onrender.com/upload")
        response = requests.post('https://projeto-fnaf.onrender.com/upload', json=payload)
        print(f"[+] Status: {response.status_code}")

        if response.status_code == 200:
            print("Conexão bem-sucedida")

        print(f"[+] Resposta: {response.text}")
    except Exception as e:
        print(f"[!] Falha ao enviar: {e}")

# Loop principal do sistema
try:
    while True:
        if desligando:
            time.sleep(1)
            continue  # Pausa a execução se o sistema está em processo de desligamento

        distancia = medir_distancia()
        print(f"[+] Distância: {distancia} cm")
        escrever_lcd("Distancia:", f"{distancia:.2f} cm")

        if distancia <= 30:
            # Distância crítica — aciona alarme e captura imagem
            set_color(1, 0, 0)
            GPIO.output(BUZZ, 1)

            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"foto_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"[+] Foto capturada: {filename}")
            else:
                print("[!] Falha ao capturar imagem")
                cap.release()
                continue
            cap.release()

            with open(filename, 'rb') as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode('utf-8')

            payload = {
                'distance_m': distancia,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'camera': 'USB',
                'image_b64': img_b64
            }

            threading.Thread(target=enviar_payload, args=(payload,)).start()

        elif distancia <= 60:
            # Alerta moderado — LED amarelo
            set_color(1, 1, 0)
            GPIO.output(BUZZ, 0)
        else:
            # Distância segura — LED azul
            set_color(0, 0, 1)
            GPIO.output(BUZZ, 0)

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[X] Encerrando...")
    GPIO.cleanup()  # Libera os GPIOs ao sair do programa
