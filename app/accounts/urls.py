from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path
from .views import UserDetailView, UserListView, UserCreateView 

urlpatterns = [
    # Signup endpoint for new users
    path("signup/", UserCreateView.as_view(), name="signup"),
    # Detail view for a specific user
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
        # List view for all users
    path("users/", UserListView.as_view(), name="user-list"),
    # JWT authentication endpoints for login and token refresh
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]