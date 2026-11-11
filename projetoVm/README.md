# 🚀 Projeto IoT & Web - Ambiente `projetoVm`

Este repositório contém o conjunto de aplicações e experimentos IoT desenvolvidos no Raspberry Pi 5, integrando automação de hardware (GPIO, sensores IR, módulos de relé), sistemas de controle viário, interface web em Flask e integração em nuvem com a API do Google Drive.

---

## 📁 Estrutura de Diretórios

```text
projetoVm/
├── semaforo/          # Controle básico do semáforo com temporização e botões
├── loja/              # Controle de fluxo de pessoas/clientes com sensores IR
└── project3/          # Sistema completo de semáforo IoT + Radar de infrações + Google Drive
    ├── app.py
    ├── credentials.json
    ├── token.json
    ├── infractions/
    ├── templates/
    │   └── index.html
    └── static/
        └── style.css
```

---

## 🛠️ Hardware Utilizado (Raspberry Pi 5)

| Componente | Tipo / Utilização | Pino BCM (GPIO) | Pino Físico |
| :--- | :--- | :--- | :--- |
| **LED Verde** | Semáforo (Saída) | `GPIO 16` | Pino 36 |
| **LED Amarelo** | Semáforo (Saída) | `GPIO 20` | Pino 38 |
| **LED Vermelho** | Semáforo (Saída) | `GPIO 21` | Pino 40 |
| **Relé Vermelho (IN1)** | Indicador de Sinal Vermelho / Infração | `GPIO 5` | Pino 29 |
| **Relé Verde (IN2)** | Indicador de Sinal Verde | `GPIO 6` | Pino 31 |
| **Sensor IR 1** | Sensor de Entrada / Linha de Infração | `GPIO 23` | Pino 16 |
| **Sensor IR 2** | Sensor de Saída | `GPIO 24` | Pino 18 |
| **Webcam USB** | Captura de evidências (OpenCV) | USB | - |

---

## 📁 Detalhamento dos Projetos

### 1. `semaforo/`
Módulo inicial focado na lógica de temporização e comutação das fases do semáforo (Verde ➔ Amarelo ➔ Vermelho).
* **Objetivo:** Estabelecer o controle de saídas digitais (`gpiozero.LED`) e a lógica de multithreading para alternância dos estados sem travar a execução principal.

---

### 2. `loja/`
Módulo desenvolvido para contagem de tráfego e ocupação em ambientes.
* **Objetivo:** Ler sinais de entrada dos sensores infravermelhos (`gpiozero.DigitalInputDevice`).
* **Lógica de Funcionamento:**
  * **IR 1 (`GPIO 23`):** Incrementa o contador de entradas.
  * **IR 2 (`GPIO 24`):** Incrementa o contador de saídas.
  * O sistema calcula em tempo real o saldo de pessoas presentes no local.

---

### 3. `project3/` (Projeto Integrado de Fiscalização Eletrônica)
Módulo avançado que une o controle viário, monitoramento por sensores IR, acionamento de relés de carga, captura de imagens por visão computacional e sincronização automática de provas de infração na nuvem.

#### ⚙️ Principais Funcionalidades:
1. **Modos de Operação:**
   * **Automático:** Alterna as fases do semáforo dinamicamente com tempos configuráveis via web.
   * **Manual:** Permite ao operador controlar o acionamento dos LEDs diretamente do painel web.
2. **Sistema de Radar de Infração:**
   * Se o semáforo estiver na cor **VERMELHA** e o **Sensor IR 1 (`GPIO 23`)** for acionado (veículo cruzando o sinal fechado):
     * O **Relé de Infração (`GPIO 5`)** é acionado por 5 segundos.
     * A webcam captura imediatamente uma foto da infração via **OpenCV**.
     * A imagem é armazenada localmente na pasta `infractions/` rotulada com Data/Hora (`YYYY-MM-DD_HH-MM-SS_Avanco_Semaforo_Vermelho.jpg`).
3. **Integração com Google Drive (OAuth 2.0):**
   * Em paralelo à gravação local, uma *thread* envia a foto capturada diretamente para a pasta configurada no Google Drive (`10gp9B8jMB7ofdw19tOjFTxE1BmcIjeqm`).
   * Mantém controle de sessão usando `credentials.json` e `token.json`.
4. **Interface Web Interativa:**
   * Desenvolvida com Flask, HTML5 e CSS3 (Design Dark/Moderno).
   * Atualização em tempo real via Fetch API (AJAX) com intervalo de polling.
   * Exibe métricas de contagem de fases, estado instantâneo dos sensores/relés e galeria do histórico de infrações com foto, data e hora.

---

## ⚡ Como Executar o Projeto Principal (`project3`)

### 1. Ativar o Ambiente Virtual
No terminal do Raspberry Pi, acesse a pasta do projeto e ative o ambiente virtual:
```bash
cd ~/Documents/projetoVm/project3
source ../bin/activate  # Ou o caminho correspondente do seu projetoVm
```

### 2. Instalar Dependências
```bash
pip install flask gpiozero opencv-python google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 3. Iniciar a Aplicação
```bash
python3 app.py
```

### 4. Acessar a Interface Web
Abra o navegador em qualquer dispositivo conectado na mesma rede local:
```text
http://<IP-DO-RASPBERRY>:5000
```
*(Exemplo: `http://10.105.77.33:5000`)*

---

## 🔑 Autenticação do Google Drive API

* O projeto está vinculado à aplicação **`infractionsCamargo`** no Google Cloud Platform.
* As credenciais do aplicativo são salvas em `credentials.json`.
* Ao rodar o sistema pela primeira vez ou registrar a primeira infração, o link de autorização será exibido no terminal para gerar o arquivo de sessão `token.json`.
* **Nota de Permissão:** O e-mail do operador (`ryanferreiradasilva2006@gmail.com`) deve estar cadastrado como **Usuário de Teste** na aba **Público-alvo / Tela de consentimento OAuth** do Google Cloud Console para liberar o token de acesso.