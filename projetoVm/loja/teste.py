from gpiozero import OutputDevice
import time

# Configura os relés (active_high=False é o padrão para a maioria dos shields de relé que acionam em nível baixo)
rele1 = OutputDevice(5, active_high=False, initial_value=False)
rele2 = OutputDevice(6, active_high=False, initial_value=False)

print("Ligando o Relé 1 (IN1 - GPIO 5)...")
rele1.on()
time.sleep(2)

print("Ligando o Relé 2 (IN2 - GPIO 6)...")
rele2.on()
time.sleep(2)

print("Desligando ambos os relés...")
rele1.off()
rele2.off()
print("Teste finalizado! Você deve ter ouvido os cliques.")