import time
import threading
from flask import Flask, render_template, request, jsonify
from gpiozero import LED, DigitalInputDevice

app = Flask(__name__)

# Configuração exata dos pinos GPIO (Raspberry Pi 5)
# LEDs do Semáforo
led_verde = LED(16)      # Pino Físico 36
led_amarelo = LED(20)    # Pino Físico 38
led_vermelho = LED(21)   # Pino Físico 40

# Sensores IR:
# Sensor IR 1 no GPIO 23 (Pino Físico 16) -> ENTRADA
# Sensor IR 2 no GPIO 24 (Pino Físico 18) -> SAÍDA
sensor_ir_1 = DigitalInputDevice(23, pull_up=True) # Pino 16 (Entrada)
sensor_ir_2 = DigitalInputDevice(24, pull_up=True) # Pino 18 (Saída)

# Variáveis globais de controle, contadores e fluxo
modo = "auto"
tempos = {"vermelho": 5, "amarelo": 2, "verde": 5}
contadores = {"vermelho": 0, "amarelo": 0, "verde": 0}
fluxo_pessoas = {"entradas": 0, "saidas": 0, "presentes": 0}

# Variáveis para evitar contagem dupla contínua (debounce)
ultimo_acionamento_1 = 0
ultimo_acionamento_2 = 0

# Tabela do Brasileirão (Corinthians em 1º)
tabela_brasileirao = [
    "Corinthians", "Flamengo", "Palmeiras", "São Paulo", 
    "Botafogo", "Fluminense", "Grêmio", "Internacional", 
    "Atlético-MG", "Cruzeiro", "Vasco", "Bahia", 
    "Fortaleza", "Athletico-PR", "Cuiabá", "Red Bull Bragantino", 
    "Criciúma", "Juventude", "Vitória", "Atlético-GO"
]

def rebaixar_corinthians():
    global tabela_brasileirao
    idx = tabela_brasileirao.index("Corinthians")
    if idx < len(tabela_brasileirao) - 1:
        tabela_brasileirao[idx], tabela_brasileirao[idx + 1] = tabela_brasileirao[idx + 1], tabela_brasileirao[idx]

def acionar_led_vermelho():
    led_vermelho.on()
    contadores["vermelho"] += 1
    rebaixar_corinthians()

def desligar_todos():
    led_vermelho.off()
    led_amarelo.off()
    led_verde.off()

def loop_semaforo():
    global modo, tempos, contadores
    while True:
        if modo == "auto":
            if modo != "auto": continue
            desligar_todos()
            led_verde.on()
            contadores["verde"] += 1
            time.sleep(tempos["verde"])

            if modo != "auto": continue
            desligar_todos()
            led_amarelo.on()
            contadores["amarelo"] += 1
            time.sleep(tempos["amarelo"])

            if modo != "auto": continue
            desligar_todos()
            acionar_led_vermelho()
            time.sleep(tempos["vermelho"])
        else:
            time.sleep(0.1)

# Monitoramento automático dos sensores IR
def loop_sensores_ir():
    global fluxo_pessoas, ultimo_acionamento_1, ultimo_acionamento_2
    while True:
        agora = time.time()
        
        # Sensor IR 1 (Entrada - GPIO 23 / Pino 16)
        if sensor_ir_1.is_active:
            if agora - ultimo_acionamento_1 > 0.8:
                fluxo_pessoas["entradas"] += 1
                fluxo_pessoas["presentes"] = fluxo_pessoas["entradas"] - fluxo_pessoas["saidas"]
                if fluxo_pessoas["presentes"] < 0:
                    fluxo_pessoas["presentes"] = 0
                ultimo_acionamento_1 = agora

        # Sensor IR 2 (Saída - GPIO 24 / Pino 18)
        if sensor_ir_2.is_active:
            if agora - ultimo_acionamento_2 > 0.8:
                fluxo_pessoas["saidas"] += 1
                fluxo_pessoas["presentes"] = fluxo_pessoas["entradas"] - fluxo_pessoas["saidas"]
                if fluxo_pessoas["presentes"] < 0:
                    fluxo_pessoas["presentes"] = 0
                ultimo_acionamento_2 = agora

        time.sleep(0.1)

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
    global modo, contadores
    if modo == "manual":
        dados = request.json
        cor = dados.get("cor")
        desligar_todos()
        if cor == "red":
            acionar_led_vermelho()
        elif cor == "yellow":
            led_amarelo.on()
            contadores["amarelo"] += 1
        elif cor == "green":
            led_verde.on()
            contadores["verde"] += 1
        return jsonify({"status": "sucesso", "cor_ativa": cor, "contadores": contadores})
    return jsonify({"status": "erro", "mensagem": "Ative o modo manual primeiro"})

@app.route("/clicar_time", methods=["POST"])
def clicar_time():
    global modo, contadores
    if modo != "manual":
        return jsonify({"status": "erro", "mensagem": "Ative o modo manual para interagir com a tabela!"})
    
    dados = request.json
    time_escolhido = dados.get("time")
    
    try:
        posicao = tabela_brasileirao.index(time_escolhido) + 1
    except ValueError:
        return jsonify({"status": "erro", "mensagem": "Time não encontrado"})

    desligar_todos()
    
    if posicao <= 4:
        led_verde.on()
        contadores["verde"] += 1
        cor_acesa = "verde"
    elif posicao <= 12:
        led_amarelo.on()
        contadores["amarelo"] += 1
        cor_acesa = "amarelo"
    else:
        acionar_led_vermelho()
        cor_acesa = "vermelho"
        
    return jsonify({"status": "sucesso", "time": time_escolhido, "posicao": posicao, "cor_acesa": cor_acesa, "contadores": contadores})

@app.route("/get_contadores", methods=["GET"])
def get_contadores():
    return jsonify(contadores)

@app.route("/get_tabela", methods=["GET"])
def get_tabela():
    return jsonify(tabela_brasileirao)

@app.route("/get_sensores", methods=["GET"])
def get_sensores():
    return jsonify({
        "ir_1": "Detectado" if sensor_ir_1.is_active else "Livre",
        "ir_2": "Detectado" if sensor_ir_2.is_active else "Livre",
        "fluxo": fluxo_pessoas
    })

@app.route("/reset_fluxo", methods=["POST"])
def reset_fluxo():
    global fluxo_pessoas
    fluxo_pessoas = {"entradas": 0, "saidas": 0, "presentes": 0}
    return jsonify({"status": "sucesso", "fluxo": fluxo_pessoas})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)