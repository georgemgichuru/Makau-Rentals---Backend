from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import json
import logging
from decimal import Decimal
from django.core.cache import cache
from accounts.models import CustomUser, Unit
from .models import Payment
from .generate_token import generate_access_token

logger = logging.getLogger(__name__)

class TestMpesaView(APIView):
    """
    Test endpoint for M-Pesa integration
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "M-Pesa test endpoint",
            "mpesa_env": settings.MPESA_ENV,
            "shortcode": settings.MPESA_SHORTCODE
        })

    def post(self, request):
        # Test token generation
        token = generate_access_token()
        if token:
            return Response({
                "success": True,
                "message": "M-Pesa token generated successfully",
                "token_preview": token[:10] + "..."
            })
        else:
            return Response({
                "success": False,
                "message": "Failed to generate M-Pesa token"
            }, status=400)
