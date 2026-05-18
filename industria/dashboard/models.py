from django.db import models

class RegistroVibracao(models.Model):
    # Identificação do Ponto de Coleta
    sensor_id = models.CharField(
        max_length=50, 
        help_text="Tag do sensor. Ex: SENS_MOT_01"
    )
    maquina_nome = models.CharField(
        max_length=100, 
        default="Motor Industrial - Banco MFPT"
    )
    
    # Métricas Derivadas
    v_rms = models.FloatField(
        help_text="Velocidade RMS em mm/s (Métrica de Severidade ISO 10816-3)"
    )
    acc_rms = models.FloatField(
        help_text="Aceleração RMS global em g (Métrica de energia global)"
    )
    kurtosis = models.FloatField(
        help_text="Kurtose do sinal (Indicador de impactos agudos / falha de rolamento)"
    )
    skewness = models.FloatField(
        help_text="Assimetria do sinal (Indicador de desgaste não uniforme)"
    )
    
    # Diagnóstico e Status da Norma
    status_iso = models.CharField(
        max_length=20,
        choices=[('NORMAL', 'Normal'), ('ALERTA', 'Alerta'), ('CRÍTICO', 'Crítico')],
        help_text="Status automático baseado nos limites da norma"
    )
    
    # Carimbo de Tempo
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora exata da coleta dos dados"
    )

    class Meta:
        verbose_name = "Registro de Vibração"
        verbose_name_plural = "Registros de Vibração"
        ordering = ['-timestamp'] # O mais recente aparece primeiro

    def __str__(self):
        # Validação de segurança para evitar erro caso o timestamp seja nulo na criação do objeto
        data_formatada = self.timestamp.strftime('%d/%m/%Y %H:%M') if self.timestamp else "Agora"
        return f"{self.sensor_id} - {self.status_iso} ({data_formatada})"