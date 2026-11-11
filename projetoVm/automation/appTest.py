import speech_recognition as sr

print("--- INICIANDO TESTE DE MICROFONE ---")

recognizer = sr.Recognizer()

# Procura o microfone USB automaticamente
mic_index = None
try:
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"Dispositivo [{index}]: {name}")
        if "USB PnP Sound Device" in name:
            mic_index = index
except Exception as e:
    print("Erro ao listar microfones:", e)

if mic_index is not None:
    print(f"\n✅ Microfone Lelong selecionado no índice: {mic_index}")
else:
    print("\n⚠️ Microfone USB não encontrado pelo nome, usando o padrão do sistema.")

try:
    with sr.Microphone(device_index=mic_index) as source:
        print("\n🎙️ Ajustando para o ruído ambiente... Fique em silêncio por 1 segundo.")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print("\n🗣️ GRAVANDO AGORA! Diga 'Abrir loja' ou 'Fechar loja' em voz alta...")
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        print("📥 Áudio capturado com sucesso! Processando na nuvem do Google...")

        # Tenta traduzir o áudio gravado
        texto = recognizer.recognize_google(audio, language="pt-BR")
        print(f"\n🎉 SUCESSO! Você disse: '{texto}'")

except sr.WaitTimeoutError:
    print("\n❌ Tempo esgotado: Nenhum som foi detectado a tempo.")
except sr.UnknownValueError:
    print("\n❌ O microfone capturou áudio, mas o Google não conseguiu entender o que foi dito.")
except sr.RequestError as e:
    print(f"\n❌ Erro de conexão com a API do Google: {e}")
except Exception as e:
    print(f"\n❌ Erro inesperado: {e}")