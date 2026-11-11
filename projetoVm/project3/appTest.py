import time
from gpiozero import DigitalInputDevice

# Configuração dos sensores IR baseada na sua pinagem
# Pino Físico 16 = GPIO 23
# Pino Físico 18 = GPIO 24
sensor_ir_1 = DigitalInputDevice(23, pull_up=True)
sensor_ir_2 = DigitalInputDevice(24, pull_up=True)

print("=== TESTE DOS SENSORES IR ATIVO ===")
print("Pressione Ctrl+C para sair.\n")

try:
    while True:
        # .is_active costuma ser False quando detecta obstáculo (dependendo do sensor)
        # Vamos ler o estado bruto e o estado traduzido
        estado_1 = "DETECTADO 🔴" if not sensor_ir_1.is_active else "Livre 🟢"
        estado_2 = "DETECTADO 🔴" if not sensor_ir_2.is_active else "Livre 🟢"
        
        print(f"Sensor IR 1 (GPIO 23): {estado_1}  |  Sensor IR 2 (GPIO 24): {estado_2}", end="\r")
        
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nTeste encerrado pelo usuário.")