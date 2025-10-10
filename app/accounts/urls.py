from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path
from .views import (UserDetailView, UserListView, UserCreateView, PasswordResetView,
                    CreatePropertyView, LandlordPropertiesView, CreateUnitView,
                    UpdatePropertyView,UpdateUnitView,UpdateUserView, SubscriptionStatusView,
                    UpdateTillNumberView, MyTokenObtainPairView, AdminLandlordSubscriptionStatusView,
                    MeView, PasswordResetConfirmView, UnitTypeListCreateView, UnitTypeDetailView,
                    LandlordDashboardStatsView, TenantUpdateUnitView, AdjustRentView,
                    PropertyUnitsView, AssignTenantToUnitView, UpdateReminderPreferencesView,
                    LandlordAvailableUnitsView,
)
urlpatterns = [
    # Signup endpoint for new users
    path("signup/", UserCreateView.as_view(), name="signup"),
    # Detail view for a specific user
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
        # List view for all users
    path("users/", UserListView.as_view(), name="user-list"),
    # JWT authentication endpoints for login and token refresh
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Endpoint for password reset requests
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    # Endpoint for password reset confirmation
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    # Endpoint to create a new property (landlord only)
    path('properties/create/', CreatePropertyView.as_view(), name='create-property'),
    # Endpoint to list all properties of the logged-in landlord
    path('properties/', LandlordPropertiesView.as_view(), name='landlord-properties'),
    # Endpoint to create a new unit under a property (landlord only)
    path('units/create/', CreateUnitView.as_view(), name='create-unit'),
    # UnitType endpoints
    path('unit-types/', UnitTypeListCreateView.as_view(), name='unittype-list-create'),
    path('unit-types/<int:pk>/', UnitTypeDetailView.as_view(), name='unittype-detail'),
    # Endpoint to update property details (landlord only)
    path('properties/<int:property_id>/update/', UpdatePropertyView.as_view(), name='update-property'),
    # Endpoint to update unit details (landlord only)
    path('units/<int:unit_id>/update/', UpdateUnitView.as_view(), name='update-unit'),
    # Endpoint to update tenant's unit number (tenant only)
    path('units/tenant/update/', TenantUpdateUnitView.as_view(), name='tenant-update-unit'),
    # Endpoint to update user details (landlord and tenant)
    path('users/<int:user_id>/update/', UpdateUserView.as_view(), name='update-user'),
    # Current user endpoint
    path('me/', MeView.as_view(), name='me'),
    #Url to check subscription status
    path('subscription_status/', SubscriptionStatusView.as_view(), name='subscription_status'),
    # Endpoint to update landlord's Mpesa till number
    path('update-till-number/', UpdateTillNumberView.as_view(), name='update-till-number'),
    # Admin section to view landlords subscription status (superuser only)
    path('admin/landlord-subscriptions/', AdminLandlordSubscriptionStatusView.as_view(), name='admin-landlord-subscriptions'),
    # Landlord dashboard statistics
    path('landlord/dashboard-stats/', LandlordDashboardStatsView.as_view(), name='landlord-dashboard-stats'),
    # Endpoint to adjust rent prices (landlord only)
    path('adjust-rent/', AdjustRentView.as_view(), name='adjust-rent'),
    # Endpoint to list units of a property (landlord only)
    path('properties/<int:property_id>/units/', PropertyUnitsView.as_view(), name='property-units'),
    # Endpoint to assign tenant to unit (landlord only)
    path('units/<int:unit_id>/assign/<int:tenant_id>/', AssignTenantToUnitView.as_view(), name='assign-tenant-to-unit'),
    # Endpoint to update tenant reminder preferences
    path('update-reminder-preferences/', UpdateReminderPreferencesView.as_view(), name='update-reminder-preferences'),
    # Endpoint to list available units for landlords to share with tenants
    path('available-units/', LandlordAvailableUnitsView.as_view(), name='landlord-available-units'),

]
