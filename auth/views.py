from django.shortcuts import render
from rest_framework.permissions import BasePermission

# [TO DO ] -> update this logic

class IsLandlordWithPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.landlord and request.user.has_perm('yourapp.can_approve_rentals')
    

# [TO DO ] -> update this logic

class ApproveRentalView(APIView):
    permission_classes = [IsLandlordWithPermission]

    def post(self, request):
        # your logic here
        return Response({"message": "Rental approved"})