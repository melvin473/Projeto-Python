import os
import json
import requests
import numpy as np
from scipy.io import loadmat
from scipy.stats import kurtosis, skew

# Configurações do Endpoint da sua API Django
URL_API = "http://127.0.0.1:8000/api/v1/telemetria/"

# Caminho para o seu arquivo de dados no Notebook
PATH_MAT = os.path.join('data', 'InnerRaceFault_vload_2.mat')

def processar_e_enviar():
    if not os.path.exists(PATH_MAT):
        print(f"Erro: Arquivo não encontrado em {PATH_MAT}")
        return

    print("📊 Lendo dados brutos do arquivo .mat...")
    raw_data = loadmat(PATH_MAT)
    struct = raw_data['bearing'][0][0]

    sinal = None
    fs = 48828 # Frequência padrão padrão caso não encontre

    for item in struct:
        if isinstance(item, np.ndarray) and item.size > 1000:
            sinal = item.flatten().astype(float)
        elif isinstance(item, np.ndarray) and item.size == 1:
            valor = float(item[0][0])
            if valor > 10000: 
                fs = valor

    if sinal is not None:
        # --- REMOVE OFFSET DC ---
        sinal = sinal - np.mean(sinal)

        # --- PROCESSAMENTO DIGITAL DE SINAIS (DSP) ---
        n = 8192
        sinal_janela = sinal[:n]
        
        # FFT normalizada
        fft_values = np.abs(np.fft.rfft(sinal_janela)) * (2.0 / n)
        freqs = np.fft.rfftfreq(n, 1/fs)
        
        # Integração para Velocidade (mm/s)
        aceleracao_mm_s2 = fft_values * 9806.65
        corte_hz = 10
        mascara = freqs > corte_hz
        
        velocidade_fft = np.zeros_like(fft_values)
        velocidade_fft[mascara] = aceleracao_mm_s2[mascara] / (2 * np.pi * freqs[mascara])
        
        # Cálculos Finais de Métricas
        v_rms = float(np.sqrt(np.sum((velocidade_fft[mascara] / np.sqrt(2))**2)))
        acc_rms = float(np.sqrt(np.mean(sinal_janela**2)))
        kurt_val = float(kurtosis(sinal))
        skew_val = float(skew(sinal))
        
        # Lógica de Classificação ISO 10816-3 (Grupo 2)
        if v_rms > 2.8:
            status_iso = "CRÍTICO"
        elif v_rms > 1.12:
            status_iso = "ALERTA"
        else:
            status_iso = "NORMAL"

        # --- MONTAGEM DO PAYLOAD JSON ---
        payload = {
            "sensor_id": "SENS_EIXO_PRINCIPAL_01",
            "maquina_nome": "Motor Industrial",
            "v_rms": round(v_rms, 2),
            "acc_rms": round(acc_rms, 2),
            "kurtosis": round(kurt_val, 2),
            "skewness": round(skew_val, 2),
            "status_iso": status_iso
        }

        print(f"🚀 Enviando payload para a API REST:\n{json.dumps(payload, indent=2)}")
        
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(URL_API, json=payload, headers=headers)
            
            if response.status_code == 201:
                print(f"✅ Sucesso! Resposta da API: {response.json()}")
            else:
                print(f"❌ Erro na API (Status {response.status_code}): {response.text}")
        except Exception as e:
            print(f"❌ Falha de conexão com o servidor Django: {e}")

if __name__ == "__main__":
    processar_e_enviar()