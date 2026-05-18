# Importação da bibliotecas necessárias
import os
import numpy as np
from django.conf import settings
from django.shortcuts import render
from scipy.io import loadmat
from scipy.signal import hilbert
from scipy.stats import kurtosis, skew
import plotly.graph_objects as go
from plotly.offline import plot
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import RegistroVibracaoSerializer
from .models import RegistroVibracao

def index(request): # Função executada ao exibir a página inicial
    # Leitura do banco de dados
    historico = RegistroVibracao.objects.all().order_by('-timestamp')[:15]
    historico_ordenado = list(reversed(historico))
    ultimo_registro = RegistroVibracao.objects.all().order_by('-timestamp').first()

    if not ultimo_registro: # Exibe "0.0" nos indicadores caso o banco de dados esteja vazio
        v_rms_atual, acc_rms_atual, kurt_atual, skew_atual, status_atual, sensor_id = 0.0, 0.0, 0.0, 0.0, "SEM DADOS", "NENHUM"
    else:
        v_rms_atual = ultimo_registro.v_rms
        acc_rms_atual = ultimo_registro.acc_rms
        kurt_atual = ultimo_registro.kurtosis
        skew_atual = ultimo_registro.skewness
        status_atual = ultimo_registro.status_iso
        sensor_id = ultimo_registro.sensor_id

    # "Termômetro" do valor RMS
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = v_rms_atual,
        title = {'text': f"Severidade Atual ({sensor_id})"},
        gauge = {'axis': {'range': [0, 6]}, 'bar': {'color': "#1e293b"},
                 'steps': [{'range': [0, 1.12], 'color': '#28a745'},
                           {'range': [1.12, 2.8], 'color': '#ffc107'},
                           {'range': [2.8, 6.0], 'color': '#dc3545'}]}
    ))
    fig_gauge.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))

    # Histórico de medições
    tempos = [r.timestamp.strftime('%H:%M:%S') for r in historico_ordenado]
    valores_rms = [r.v_rms for r in historico_ordenado]
    status_lista = [r.status_iso for r in historico_ordenado]

    fig_tendencia = go.Figure()
    fig_tendencia.add_trace(go.Scatter(
        x=tempos, y=valores_rms, mode='lines+markers', name='Velocidade RMS',
        line=dict(color='#0284c7', width=3),
        marker=dict(size=8, color=['#dc3545' if s == 'CRÍTICO' else '#ffc107' if s == 'ALERTA' else '#28a745' for s in status_lista])
    ))
    fig_tendencia.add_hline(y=1.12, line_dash="dash", line_color="#ffc107")
    fig_tendencia.add_hline(y=2.8, line_dash="dash", line_color="#dc3545")
    
    max_y = max(valores_rms) + 1 if valores_rms else 4
    fig_tendencia.update_layout(title="Histórico de Evolução Temporal (API)", xaxis_title="Hora da Coleta", yaxis_title="mm/s", height=320, margin=dict(l=40, r=20, t=50, b=40))

    # Inicialização do contexto base
    context = {
        'grafico_gauge': fig_gauge.to_html(full_html=False),
        'grafico_tendencia': fig_tendencia.to_html(full_html=False),
        'v_rms': round(v_rms_atual, 2),
        'acc_rms': round(acc_rms_atual, 2),
        'kurtosis': round(kurt_atual, 2),
        'skewness': round(skew_atual, 2),
        'status_iso': status_atual,
        'grafico_fft': None, # Evita que o template quebre se não houver gráficos
        'grafico_envelope': None
    }

    # Função executada na guia Diagnóstico
    if request.method == 'POST':
        action = request.POST.get('action')
        raw_data = None
        
        try:
            # Executada quando um arquivo .mat é carregado
            if action == 'upload' and request.FILES.get('arquivo_mat'):
                arquivo_enviado = request.FILES['arquivo_mat']
                context['arquivo_analisado'] = arquivo_enviado.name
                raw_data = loadmat(arquivo_enviado)
                
            # Executada ao clicar no botão "Carregar Amostra Padrão"
            elif action == 'demo':
                # Altere 'data' para 'amostras' caso mude o nome da pasta no notebook
                caminho_amostra = os.path.join(os.path.dirname(__file__), 'data', 'InnerRaceFault_vload_1.mat')
                
                context['arquivo_analisado'] = os.path.basename(caminho_amostra) + " (Demonstração)"
                raw_data = loadmat(caminho_amostra)

            # Processamento dos dados
            if raw_data is not None:
                struct = None
                for key in raw_data.keys():
                    if not key.startswith('__'):
                        struct = raw_data[key][0][0]
                        break

                sinal = None
                fs = 48828

                if struct is not None:
                    for item in struct:
                        if isinstance(item, np.ndarray) and item.size > 1000:
                            sinal = item.flatten().astype(float)
                        elif isinstance(item, np.ndarray) and item.size == 1:
                            valor = float(item[0][0])
                            if valor > 10000: fs = valor

                if sinal is not None:
                    sinal = sinal - np.mean(sinal)
                    n = 8192
                    sinal_janela = sinal[:n]

                    # Cálculo da FFT
                    fft_values = np.abs(np.fft.rfft(sinal_janela)) * (2.0 / n)
                    freqs = np.fft.rfftfreq(n, 1/fs)

                    # Cálculo do Envelope
                    n_env = 2000
                    envelope = np.abs(hilbert(sinal[:n_env]))
                    eixo_tempo_env = np.linspace(0, n_env/fs, n_env)

                    # Métricas do arquivo
                    context['file_kurtosis'] = round(float(kurtosis(sinal)), 2)
                    context['file_skewness'] = round(float(skew(sinal)), 2)
                    context['file_fs'] = int(fs)

                    # Gráfico FFT
                    fig_fft = go.Figure()
                    fig_fft.add_trace(go.Scatter(x=freqs.tolist(), y=fft_values.tolist(), line=dict(color='#1f77b4', width=1)))
                    fig_fft.update_layout(title="Espectro de Frequência (Aceleração)", xaxis_title="Hz", yaxis_title="Amplitude (g)", height=350, template="plotly_white")
                    context['grafico_fft'] = fig_fft.to_html(full_html=False)

                    # Gráfico Envelope
                    fig_env = go.Figure()
                    fig_env.add_trace(go.Scatter(x=eixo_tempo_env.tolist(), y=sinal[:n_env].tolist(), name="Sinal Bruto", line=dict(color='lightgray', width=1)))
                    fig_env.add_trace(go.Scatter(x=eixo_tempo_env.tolist(), y=envelope.tolist(), name="Envelope", line=dict(color='red', width=1.5)))
                    fig_env.update_layout(title="Demodulação por Envelope (Impactos)", xaxis_title="Segundos", yaxis_title="g", height=350, template="plotly_white")
                    context['grafico_envelope'] = fig_env.to_html(full_html=False)

        except Exception as e:
            context['arquivo_analisado'] = f"Erro ao processar: {e}"

    return render(request, 'dashboard/index.html', context)

class TelemetriaVibracaoAPIView(APIView): 
    def get(self, request):
        registros = RegistroVibracao.objects.all().order_by('-timestamp')[:20]
        serializer = RegistroVibracaoSerializer(registros, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RegistroVibracaoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "Amostra registrada com sucesso",
                "dados": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)