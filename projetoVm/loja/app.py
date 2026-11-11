import time
import threading
from flask import Flask, render_template, request, jsonify
from gpiozero import LED, DigitalInputDevice, OutputDevice

app = Flask(__name__)

# Configuração exata dos pinos GPIO (Raspberry Pi 5)
# LEDs do Semáforo
led_verde = LED(16)      # Pino Físico 36
led_amarelo = LED(20)    # Pino Físico 38
led_vermelho = LED(21)   # Pino Físico 40

# Shield Relé (GPIO 5 = Pino 29 | GPIO 6 = Pino 31)
rele_in1 = OutputDevice(5, active_high=False, initial_value=False)
rele_in2 = OutputDevice(6, active_high=False, initial_value=False)

# Sensores IR (GPIO 23 = Pino 16 [Entrada] | GPIO 24 = Pino 18 [Saída])
sensor_ir_1 = DigitalInputDevice(23, pull_up=True)
sensor_ir_2 = DigitalInputDevice(24, pull_up=True)

# Variáveis globais de controle, contadores e fluxo
modo = "auto"
tempos = {"vermelho": 5, "amarelo": 2, "verde": 5}
contadores = {"vermelho": 0, "amarelo": 0, "verde": 0}
fluxo_pessoas = {"entradas": 0, "saidas": 0, "presentes": 0}

# Variáveis para controlar o modo manual dos relés (se ativado manualmente, ignora o automático temporariamente)
modo_rele_manual = False

# Estados anteriores para controlar a borda de subida/descida (evita contar enquanto parado)
estado_anterior_ir1 = False
estado_anterior_ir2 = False

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

def atualizar_reles_automatico():
    """Gerencia o acionamento automático dos relés baseado nas pessoas presentes (se não estiver em manual)"""
    global modo_rele_manual
    if modo_rele_manual:
        return  # Se o usuário assumiu o controle manual dos relés, o automático não interfere
        
    presentes = fluxo_pessoas["presentes"]
    if presentes >= 10:
        rele_in1.on()
        rele_in2.on()
    elif presentes > 5:
        rele_in1.on()
        rele_in2.off()
    else:
        rele_in1.off()
        rele_in2.off()

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

# Monitoramento de sensores com lógica de transição (só conta na mudança de Livre -> Detectado)
def loop_sensores_ir():
    global fluxo_pessoas, estado_anterior_ir1, estado_anterior_ir2
    while True:
        atual_ir1 = sensor_ir_1.is_active  # True se detectado
        atual_ir2 = sensor_ir_2.is_active  # True se detectado

        if atual_ir1 and not estado_anterior_ir1:
            fluxo_pessoas["entradas"] += 1
            fluxo_pessoas["presentes"] = fluxo_pessoas["entradas"] - fluxo_pessoas["saidas"]
            if fluxo_pessoas["presentes"] < 0:
                fluxo_pessoas["presentes"] = 0
            atualizar_reles_automatico()

        if atual_ir2 and not estado_anterior_ir2:
            fluxo_pessoas["saidas"] += 1
            fluxo_pessoas["presentes"] = fluxo_pessoas["entradas"] - fluxo_pessoas["saidas"]
            if fluxo_pessoas["presentes"] < 0:
                fluxo_pessoas["presentes"] = 0
            atualizar_reles_automatico()

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
        "fluxo": fluxo_pessoas,
        "reles": {
            "in1": "Ligado" if rele_in1.is_active else "Desligado",
            "in2": "Ligado" if rele_in2.is_active else "Desligado",
            "modo_manual": modo_rele_manual
        }
    })

@app.route("/reset_fluxo", methods=["POST"])
def reset_fluxo():
    global fluxo_pessoas, modo_rele_manual
    fluxo_pessoas = {"entradas": 0, "saidas": 0, "presentes": 0}
    modo_rele_manual = False # Volta pro automático ao resetar
    atualizar_reles_automatico()
    return jsonify({"status": "sucesso", "fluxo": fluxo_pessoas})

# Rota para controle manual dos relés pela interface
@app.route("/controlar_rele_manual", methods=["POST"])
def controlar_rele_manual():
    global modo_rele_manual
    modo_rele_manual = True # Ativa o travamento manual
    
    dados = request.json
    rele = dados.get("rele")
    acao = dados.get("acao") # "ligar" ou "desligar"

    if rele == "in1":
        if acao == "ligar": rele_in1.on()
        else: rele_in1.off()
    elif rele == "in2":
        if acao == "ligar": rele_in2.on()
        else: rele_in2.off()

    return jsonify({"status": "sucesso"})

# Rota para reativar o modo automático dos relés
@app.route("/ativar_rele_auto", methods=["POST"])
def ativar_rele_auto():
    global modo_rele_manual
    modo_rele_manual = False
    atualizar_reles_automatico()
    return jsonify({"status": "sucesso"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)


