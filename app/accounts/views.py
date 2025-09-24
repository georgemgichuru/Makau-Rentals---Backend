from django.shortcuts import render
from serializers import UserSerializer
from models import CustomUser
from rest_framework.response import Response
from rest_framework.views import APIView

#Lists all users both tenants and landlords
class UserDetailView(APIView):
    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

# To list the lis of all users
# TODO: List only for admin users and list only tenants for landlords
class UserListView(APIView):
    def get(self, request):
        tenants = CustomUser.objects.filter(user_type='tenant')
        serializer = UserSerializer(tenants, many=True)
        return Response(serializer.data)
    
# To create a new user basically for registration
class UserCreateView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)