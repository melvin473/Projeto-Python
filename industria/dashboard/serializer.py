from rest_framework import serializers
from .models import RegistroVibracao

class RegistroVibracaoSerializer(serializers.ModelSerializer):
    # Campo calculado para mostrar o status formatado na API se precisar
    class Meta:
        model = RegistroVibracao
        fields = '__all__' # Expõe todos os campos: id, sensor_id, v_rms, kurtosis, timestamp...