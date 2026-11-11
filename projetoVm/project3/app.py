import os
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from gpiozero import LED, DigitalInputDevice, OutputDevice
import cv2

# Importações do Google Drive API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

# Configuração da pasta local de infrações
PASTA_INFRACOES = os.path.join(os.getcwd(), 'infractions')
if not os.path.exists(PASTA_INFRACOES):
    os.makedirs(PASTA_INFRACOES)

# Configuração do Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']
GOOGLE_DRIVE_FOLDER_ID = '10gp9B8jMB7ofdw19tOjFTxE1BmcIjeqm'

def autenticar_google_drive():
    """Autentica e retorna o serviço da API do Google Drive"""
    creds = None
    token_path = 'token.json'
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def enviar_para_google_drive(caminho_arquivo, nome_arquivo):
    """Envia o arquivo de imagem para a pasta do Google Drive em background"""
    try:
        service = autenticar_google_drive()
        file_metadata = {
            'name': nome_arquivo,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(caminho_arquivo, mimetype='image/jpeg')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"☁️ Sucesso! Foto enviada para o Google Drive. ID do arquivo: {file.get('id')}")
    except Exception as e:
        print("❌ Erro ao enviar foto para o Google Drive:", e)

# Lista em memória para armazenar o histórico de infrações para o site
historico_infracoes = []

# Configuração dos LEDs do Semáforo (Raspberry Pi 5)
led_verde = LED(21)      # Pino Físico 36
led_amarelo = LED(20)    # Pino Físico 38
led_vermelho = LED(16)   # Pino Físico 40

# Relés atrelados ao estado do semáforo
# GPIO 5 (Pino 29 / IN1) - Acionado no Vermelho (Infração)
rele_vermelho = OutputDevice(5, active_high=False, initial_value=False)
# GPIO 6 (Pino 31 / IN2) - Acionado no Verde
rele_verde = OutputDevice(6, active_high=False, initial_value=False)

# Sensores IR (GPIO 23 = Pino 16 [Entrada] | GPIO 24 = Pino 18 [Saída])
sensor_ir_1 = DigitalInputDevice(23, pull_up=True)
sensor_ir_2 = DigitalInputDevice(24, pull_up=True)

# Variáveis globais de controle
modo = "auto"
cor_atual_semaforo = "verde"  # Guarda a cor atual ativa do semáforo
tempos = {"vermelho": 5, "amarelo": 2, "verde": 5}
contadores = {"vermelho": 0, "amarelo": 0, "verde": 0}
fluxo_pessoas = {"entradas": 0, "saidas": 0, "presentes": 0}

estado_anterior_ir1 = False
estado_anterior_ir2 = False

def desligar_todos():
    led_vermelho.off()
    led_amarelo.off()
    led_verde.off()
    rele_vermelho.off()
    rele_verde.off()

def atualizar_reles_por_cor(cor):
    if cor == "vermelho":
        rele_vermelho.on()
        rele_verde.off()
    elif cor == "verde":
        rele_vermelho.off()
        rele_verde.on()
    else:
        rele_vermelho.off()
        rele_verde.off()

def capturar_foto_infracao(motivo="Avanco_Semaforo_Vermelho"):
    """Captura uma imagem utilizando o OpenCV (Webcam) e salva na pasta infractions"""
    global historico_infracoes
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Erro: Não foi possível abrir a webcam com OpenCV.")
            return

        ret, frame = cap.read()
        cap.release()

        if ret:
            agora = datetime.now()
            nome_arquivo = f"{agora.strftime('%Y-%m-%d_%H-%M-%S')}_{motivo}.jpg"
            caminho_completo = os.path.join(PASTA_INFRACOES, nome_arquivo)
            
            # Salva localmente
            cv2.imwrite(caminho_completo, frame)
            
            # Envia para o Google Drive em uma thread separada
            threading.Thread(target=enviar_para_google_drive, args=(caminho_completo, nome_arquivo), daemon=True).start()
            
            dia_str = agora.strftime('%d/%m/%Y')
            hora_str = agora.strftime('%H:%M:%S')
            
            info_infracao = {
                "id": len(historico_infracoes) + 1,
                "dia": dia_str,
                "hora": hora_str,
                "motivo": motivo,
                "imagem": nome_arquivo
            }
            
            historico_infracoes.insert(0, info_infracao)
            print(f"🚨 INFRAÇÃO REGISTRADA! Foto salva e agendada para o Google Drive: {nome_arquivo}")
        else:
            print("Erro: Falha ao ler o frame da webcam.")
    except Exception as e:
        print("Erro na captura da infração com OpenCV:", e)

def acionar_rele_infracao_temporizado():
    """Ativa o relé vermelho (GPIO 5) por 5 segundos e tira a foto em background"""
    def tarefa():
        print("⚡ Relé de infração acionado no Vermelho (Ligado por 5s)...")
        rele_vermelho.on()
        capturar_foto_infracao("Avanco_Semaforo_Vermelho")
        time.sleep(5)
        if cor_atual_semaforo != "vermelho":
            rele_vermelho.off()
            print("⚡ Relé desativado após 5s.")
    
    threading.Thread(target=tarefa, daemon=True).start()

def loop_semaforo():
    global modo, tempos, contadores, cor_atual_semaforo
    while True:
        if modo == "auto":
            # --- VERDE ---
            if modo != "auto": continue
            cor_atual_semaforo = "verde"
            desligar_todos()
            led_verde.on()
            atualizar_reles_por_cor("verde")
            contadores["verde"] += 1
            time.sleep(tempos["verde"])

            # --- AMARELO ---
            if modo != "auto": continue
            cor_atual_semaforo = "amarelo"
            desligar_todos()
            led_amarelo.on()
            atualizar_reles_por_cor("amarelo")
            contadores["amarelo"] += 1
            time.sleep(tempos["amarelo"])

            # --- VERMELHO ---
            if modo != "auto": continue
            cor_atual_semaforo = "vermelho"
            desligar_todos()
            led_vermelho.on()
            atualizar_reles_por_cor("vermelho")
            contadores["vermelho"] += 1
            time.sleep(tempos["vermelho"])
        else:
            time.sleep(0.1)

def loop_sensores_ir():
    global fluxo_pessoas, estado_anterior_ir1, estado_anterior_ir2, cor_atual_semaforo
    while True:
        atual_ir1 = sensor_ir_1.is_active
        atual_ir2 = sensor_ir_2.is_active

        # Sensor IR 1 (GPIO 23) - Entrada / Detecção de passagem
        if atual_ir1 and not estado_anterior_ir1:
            fluxo_pessoas["entradas"] += 1
            fluxo_pessoas["presentes"] = fluxo_pessoas["entradas"] - fluxo_pessoas["saidas"]
            if fluxo_pessoas["presentes"] < 0: fluxo_pessoas["presentes"] = 0

            # REGRA DA INFRAÇÃO: Passou no IR 1 (GPIO 23) com o semáforo VERMELHO
            if cor_atual_semaforo == "vermelho":
                acionar_rele_infracao_temporizado()

        # Sensor IR 2 (GPIO 24) - Saída
        if atual_ir2 and not estado_anterior_ir2:
            fluxo_pessoas["saidas"] += 1
            fluxo_pessoas["presentes"] = fluxo_pessoas["entradas"] - fluxo_pessoas["saidas"]
            if fluxo_pessoas["presentes"] < 0: fluxo_pessoas["presentes"] = 0

        estado_anterior_ir1 = atual_ir1
        estado_anterior_ir2 = atual_ir2
        time.sleep(0.05)

# Inicia as threads em segundo plano
threading.Thread(target=loop_semaforo, daemon=True).start()
threading.Thread(target=loop_sensores_ir, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/set_modo", methods=["POST"])
def set_modo():
    global modo
    dados = request.json
    modo = dados.get("modo")
    desligar_todos()
    return jsonify({"status": "sucesso", "modo": modo})

@app.route("/set_tempo", methods=["POST"])
def set_tempo():
    global tempos
    dados = request.json
    cor = dados.get("cor")
    valor = int(dados.get("valor"))
    if cor in tempos:
        tempos[cor] = valor
    return jsonify({"status": "sucesso", "tempos": tempos})

@app.route("/controlar_manual", methods=["POST"])
def controlar_manual():
    global modo, contadores, cor_atual_semaforo
    if modo == "manual":
        dados = request.json
        cor = dados.get("cor")
        desligar_todos()
        if cor == "red":
            cor_atual_semaforo = "vermelho"
            led_vermelho.on()
            atualizar_reles_por_cor("vermelho")
            contadores["vermelho"] += 1
        elif cor == "yellow":
            cor_atual_semaforo = "amarelo"
            led_amarelo.on()
            atualizar_reles_por_cor("amarelo")
            contadores["amarelo"] += 1
        elif cor == "green":
            cor_atual_semaforo = "verde"
            led_verde.on()
            atualizar_reles_por_cor("verde")
            contadores["verde"] += 1
        return jsonify({"status": "sucesso", "cor_ativa": cor, "contadores": contadores})
    return jsonify({"status": "erro", "mensagem": "Ative o modo manual primeiro"})

@app.route("/registrar_infracao", methods=["POST"])
def rota_registrar_infracao():
    dados = request.json or {}
    motivo = dados.get("motivo", "Infracao_Manual")
    capturar_foto_infracao(motivo)
    return jsonify({"status": "sucesso", "infracoes": historico_infracoes})

@app.route("/get_infracoes", methods=["GET"])
def get_infracoes():
    return jsonify(historico_infracoes)

@app.route('/infractions/<path:filename>')
def serve_infraction_image(filename):
    return send_from_directory(PASTA_INFRACOES, filename)

@app.route("/get_contadores", methods=["GET"])
def get_contadores():
    return jsonify(contadores)

@app.route("/get_sensores", methods=["GET"])
def get_sensores():
    return jsonify({
        "ir_1": "Detectado" if sensor_ir_1.is_active else "Livre",
        "ir_2": "Detectado" if sensor_ir_2.is_active else "Livre",
        "fluxo": fluxo_pessoas,
        "reles": {
            "in1": "Ligado" if rele_vermelho.is_active else "Desligado",
            "in2": "Ligado" if rele_verde.is_active else "Desligado"
        }
    })

@app.route("/reset_fluxo", methods=["POST"])
def reset_fluxo():
    global fluxo_pessoas
    fluxo_pessoas = {"entradas": 0, "saidas": 0, "presentes": 0}
    return jsonify({"status": "sucesso", "fluxo": fluxo_pessoas})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)