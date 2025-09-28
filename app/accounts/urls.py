from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path
from .views import (UserDetailView, UserListView, UserCreateView, PasswordResetView, 
                    CreatePropertyView, LandlordPropertiesView, CreateUnitView,
                    UpdatePropertyView,UpdateUnitView,UpdateUserView
)
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
    # Endpoint for password reset requests
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    # Endpoint to create a new property (landlord only)
    path('properties/create/', CreatePropertyView.as_view(), name='create-property'),
    # Endpoint to list all properties of the logged-in landlord
    path('properties/', LandlordPropertiesView.as_view(), name='landlord-properties'),
    # Endpoint to create a new unit under a property (landlord only)
    path('units/create/', CreateUnitView.as_view(), name='create-unit'),
    # Endpoint to update property details (landlord only)
    path('properties/<int:property_id>/update/', UpdatePropertyView.as_view(), name='update-property'),
    # Endpoint to update unit details (landlord only)
    path('units/<int:unit_id>/update/', UpdateUnitView.as_view(), name='update-unit'),
    # Endpoint to update user details (landlord and tenant)
    path('users/<int:user_id>/update/', UpdateUserView.as_view(), name='update-user'),
]