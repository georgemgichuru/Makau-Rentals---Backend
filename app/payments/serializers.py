from rest_framework import serializers
from .models import Payment, SubscriptionPayment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['transaction_date', 'status']


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPayment
        fields = '__all__'
        read_only_fields = ['transaction_date']
