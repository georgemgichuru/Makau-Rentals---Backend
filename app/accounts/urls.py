from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path
from .views import (UserDetailView, UserListView, UserCreateView, PasswordResetView,
                    CreatePropertyView, LandlordPropertiesView, CreateUnitView,
                    UpdatePropertyView,UpdateUnitView,UpdateUserView, SubscriptionStatusView,
                    UpdateTillNumberView, MyTokenObtainPairView, AdminLandlordSubscriptionStatusView,
                    MeView, PasswordResetConfirmView, UnitTypeListCreateView, UnitTypeDetailView,
                    LandlordDashboardStatsView, TenantUpdateUnitView, AdjustRentView,
                    PropertyUnitsView, AssignTenantView, UpdateReminderPreferencesView,
                    LandlordAvailableUnitsView, WelcomeView, LandlordsListView,
                    PendingApplicationsView, EvictedTenantsView,TenantRegistrationStepView,
                    LandlordRegistrationStepView,CompleteTenantRegistrationView,CompleteLandlordRegistrationView,
)

router = DefaultRouter()
# Remove or comment these out if you're not using ViewSets
# router.register('properties', views.PropertyViewSet, basename='property')
# router.register('units', views.UnitViewSet, basename='unit')
# router.register('users', views.UserViewSet, basename='user')

urlpatterns = [
    # Authentication endpoints
    path("signup/", UserCreateView.as_view(), name="signup"),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User endpoints
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("users/", UserListView.as_view(), name="user-list"),
    path('users/<int:user_id>/update/', UpdateUserView.as_view(), name='user-update'),
    path('me/', MeView.as_view(), name='me'),

    # Password reset
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Property endpoints - FIXED URL NAMES
    path('properties/create/', CreatePropertyView.as_view(), name='property-create'),  # Changed from 'create-property'
    path('properties/', LandlordPropertiesView.as_view(), name='property-list'),  # Changed from 'landlord-properties'
    path('properties/<int:property_id>/update/', UpdatePropertyView.as_view(), name='property-update'),
    path('properties/<int:property_id>/units/', PropertyUnitsView.as_view(), name='property-units'),

    # Unit endpoints - FIXED URL NAMES
    path('units/create/', CreateUnitView.as_view(), name='unit-create'),  # Changed from 'create-unit'
    path('units/<int:unit_id>/update/', UpdateUnitView.as_view(), name='unit-update'),
    path('units/tenant/update/', TenantUpdateUnitView.as_view(), name='tenant-unit-update'),
    path('units/<int:unit_id>/assign/<int:tenant_id>/', AssignTenantView.as_view(), name='assign-tenant'),  # Changed from 'assign-tenant-to-unit'

    # UnitType endpoints
    path('unit-types/', UnitTypeListCreateView.as_view(), name='unit-types'),  # Changed from 'unittype-list-create'
    path('unit-types/<int:pk>/', UnitTypeDetailView.as_view(), name='unit-type-detail'),  # Changed from 'unittype-detail'

    # Subscription endpoints
    path('subscription-status/', SubscriptionStatusView.as_view(), name='subscription-status'),
    path('update-till-number/', UpdateTillNumberView.as_view(), name='update-till-number'),
    path('admin/landlord-subscriptions/', AdminLandlordSubscriptionStatusView.as_view(), name='admin-landlord-subscriptions'),
    path('dashboard-stats/', LandlordDashboardStatsView.as_view(), name='dashboard-stats'),
    path('adjust-rent/', AdjustRentView.as_view(), name='adjust-rent'),

    # Other endpoints
    path('update-reminder-preferences/', UpdateReminderPreferencesView.as_view(), name='update-reminder-preferences'),
    path('available-units/', LandlordAvailableUnitsView.as_view(), name='available-units'),  # Changed from 'landlord-available-units'
    path('welcome/', WelcomeView.as_view(), name='welcome'),

    # New endpoints for contexts
    path('tenants/', UserListView.as_view(), name='tenants-list'),
    path('landlords/', LandlordsListView.as_view(), name='landlords-list'),
    path('pending-applications/', PendingApplicationsView.as_view(), name='pending-applications'),
    path('evicted-tenants/', EvictedTenantsView.as_view(), name='evicted-tenants'),

    path('auth/tenant/step/<int:step>/', TenantRegistrationStepView.as_view(), name='tenant-registration-step'),
    path('auth/landlord/step/<int:step>/', LandlordRegistrationStepView.as_view(), name='landlord-registration-step'),
    path('auth/tenant/complete/', CompleteTenantRegistrationView.as_view(), name='complete-tenant-registration'),
    path('auth/landlord/complete/', CompleteLandlordRegistrationView.as_view(), name='complete-landlord-registration'),
]
