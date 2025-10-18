from rest_framework import serializers
from .models import Payment, SubscriptionPayment


class PaymentSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source='transaction_date', read_only=True)
    phone = serializers.CharField(source='tenant.phone_number', read_only=True)
    tenant_name = serializers.CharField(source='tenant.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'tenant', 'tenant_name', 'unit', 'payment_type', 'amount', 'mpesa_receipt', 'date', 'phone', 'status']
        read_only_fields = ['transaction_date', 'status']


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPayment
        fields = '__all__'
        read_only_fields = ['transaction_date']
