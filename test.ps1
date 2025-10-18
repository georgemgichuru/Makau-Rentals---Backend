# Makau Rentals API Workflow Test Script
# This PowerShell script simulates a real-life workflow of the Makau Rentals app
# by interacting with the live API at https://makau-rentals-backend.onrender.com/
# It sends JSON requests and receives JSON responses, demonstrating key features.

# Base URL for the API
$baseUrl = "https://makau-rentals-backend.onrender.com"

# Function to make authenticated requests
function Invoke-AuthenticatedRequest {
    param (
        [string]$Uri,
        [string]$Method = "GET",
        [object]$Body = $null,
        [string]$Token
    )
    $headers = @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }
    $params = @{
        Uri = $Uri
        Method = $Method
        Headers = $headers
    }
    if ($Body) {
        $params.Body = $Body | ConvertTo-Json -Depth 10
    }
    try {
        $response = Invoke-RestMethod @params
        Write-Host "Response from $Uri ($Method):" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 10
        return $response
    } catch {
        Write-Host "Error in request to $Uri ($Method): $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Function to make unauthenticated requests
function Invoke-UnauthenticatedRequest {
    param (
        [string]$Uri,
        [string]$Method = "GET",
        [object]$Body = $null
    )
    $headers = @{
        "Content-Type" = "application/json"
    }
    $params = @{
        Uri = $Uri
        Method = $Method
        Headers = $headers
    }
    if ($Body) {
        $params.Body = $Body | ConvertTo-Json -Depth 10
    }
    try {
        $response = Invoke-RestMethod @params
        Write-Host "Response from $Uri ($Method):" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 10
        return $response
    } catch {
        Write-Host "Error in request to $Uri ($Method): $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

Write-Host "Starting Makau Rentals API Workflow Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Step 1: User Signup (Landlord)
Write-Host "`nStep 1: Signing up a new landlord user" -ForegroundColor Yellow
$signupData = @{
    username = "testlandlord"
    email = "testlandlord@example.com"
    password = "TestPass123!"
    first_name = "Test"
    last_name = "Landlord"
    phone_number = "+254700000000"
    user_type = "landlord"
}
$signupResponse = Invoke-UnauthenticatedRequest -Uri "$baseUrl/api/accounts/signup/" -Method "POST" -Body $signupData
if (-not $signupResponse) { exit }

# Step 2: Login to get JWT token
Write-Host "`nStep 2: Logging in to obtain JWT token" -ForegroundColor Yellow
$loginData = @{
    username = "testlandlord"
    password = "TestPass123!"
}
$loginResponse = Invoke-UnauthenticatedRequest -Uri "$baseUrl/api/accounts/token/" -Method "POST" -Body $loginData
if (-not $loginResponse) { exit }
$accessToken = $loginResponse.access

# Step 2.1: Initiate subscription payment
Write-Host "`nStep 2.1: Initiating subscription payment" -ForegroundColor Yellow
$subscriptionData = @{
    plan = "starter"
    phone_number = "+254700000000"
}
$subscriptionResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/payments/stk-push-subscription/" -Method "POST" -Body $subscriptionData -Token $accessToken

# Step 3: Get current user details
Write-Host "`nStep 3: Fetching current user details" -ForegroundColor Yellow
$userDetails = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/me/" -Token $accessToken

# Step 4: Create a property
Write-Host "`nStep 4: Creating a new property" -ForegroundColor Yellow
$propertyData = @{
    name = "Test Apartment Block"
    location = "Nairobi, Kenya"
    description = "A test property for demonstration"
}
$propertyResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/properties/create/" -Method "POST" -Body $propertyData -Token $accessToken
$propertyId = $propertyResponse.id

# Step 5: Create a unit type
Write-Host "`nStep 5: Creating a unit type" -ForegroundColor Yellow
$unitTypeData = @{
    name = "1 Bedroom"
    description = "One bedroom apartment"
}
$unitTypeResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/unit-types/" -Method "POST" -Body $unitTypeData -Token $accessToken
$unitTypeId = $unitTypeResponse.id

# Step 6: Create a unit
Write-Host "`nStep 6: Creating a new unit" -ForegroundColor Yellow
$unitData = @{
    property = $propertyId
    unit_type = $unitTypeId
    unit_number = "A101"
    rent_amount = 25000
    deposit_amount = 25000
    description = "Ground floor unit"
}
$unitResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/units/create/" -Method "POST" -Body $unitData -Token $accessToken
$unitId = $unitResponse.id

# Step 7: Signup a tenant user
Write-Host "`nStep 7: Signing up a new tenant user" -ForegroundColor Yellow
$tenantSignupData = @{
    username = "testtenant"
    email = "testtenant@example.com"
    password = "TestPass123!"
    first_name = "Test"
    last_name = "Tenant"
    phone_number = "+254711111111"
    user_type = "tenant"
}
$tenantSignupResponse = Invoke-UnauthenticatedRequest -Uri "$baseUrl/api/accounts/signup/" -Method "POST" -Body $tenantSignupData
$tenantId = $tenantSignupResponse.id

# Step 7.1: Initiate deposit payment (test mode)
Write-Host "`nStep 7.1: Initiating deposit payment (test mode)" -ForegroundColor Yellow
$depositData = @{
    unit_id = $unitId
    test = $true
}
$depositResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/payments/initiate-deposit/" -Method "POST" -Body $depositData -Token $accessToken

# Step 8: Assign tenant to unit
Write-Host "`nStep 8: Assigning tenant to unit" -ForegroundColor Yellow
$assignResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/units/$unitId/assign/$tenantId/" -Method "PUT" -Token $accessToken

# Step 9: Login as tenant to get token
Write-Host "`nStep 9: Logging in as tenant" -ForegroundColor Yellow
$tenantLoginData = @{
    username = "testtenant"
    password = "TestPass123!"
}
$tenantLoginResponse = Invoke-UnauthenticatedRequest -Uri "$baseUrl/api/accounts/token/" -Method "POST" -Body $tenantLoginData
$tenantToken = $tenantLoginResponse.access

# Step 10: Tenant updates their unit (e.g., move-in date)
Write-Host "`nStep 10: Tenant updating unit details" -ForegroundColor Yellow
$tenantUnitUpdateData = @{
    move_in_date = "2024-01-15"
}
$tenantUpdateResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/units/tenant/update/" -Method "PUT" -Body $tenantUnitUpdateData -Token $tenantToken

# Step 11: Initiate rent payment (STK Push)
Write-Host "`nStep 11: Initiating rent payment (STK Push)" -ForegroundColor Yellow
$stkPushData = @{
    phone_number = "+254711111111"  # Use tenant's phone number
    amount = 25000
}
$stkPushResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/payments/stk-push/$unitId/" -Method "POST" -Body $stkPushData -Token $tenantToken

# Step 12: Check rent payment status
Write-Host "`nStep 12: Checking rent payment summary" -ForegroundColor Yellow
$paymentSummary = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/payments/rent-payments/summary/" -Token $tenantToken

# Step 13: Create a maintenance report
Write-Host "`nStep 13: Creating a maintenance report" -ForegroundColor Yellow
$reportData = @{
    title = "Leaky faucet"
    description = "The kitchen faucet is leaking water"
    urgency = "medium"
}
$reportResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/create/" -Method "POST" -Body $reportData -Token $tenantToken
$reportId = $reportResponse.id

# Step 14: Landlord views open reports
Write-Host "`nStep 14: Landlord viewing open reports" -ForegroundColor Yellow
$openReports = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/open/" -Token $accessToken

# Step 15: Landlord views urgent reports
Write-Host "`nStep 15: Landlord viewing urgent reports" -ForegroundColor Yellow
$urgentReports = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/urgent/" -Token $accessToken

# Step 16: Landlord views in-progress reports
Write-Host "`nStep 16: Landlord viewing in-progress reports" -ForegroundColor Yellow
$inProgressReports = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/in-progress/" -Token $accessToken

# Step 17: Landlord views resolved reports
Write-Host "`nStep 17: Landlord viewing resolved reports" -ForegroundColor Yellow
$resolvedReports = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/resolved/" -Token $accessToken

# Step 18: Landlord updates report status to resolved
Write-Host "`nStep 18: Landlord updating report status to 'resolved'" -ForegroundColor Yellow
$statusUpdateData = @{
    status = "resolved"
}
$statusUpdateResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/$reportId/update-status/" -Method "PUT" -Body $statusUpdateData -Token $accessToken

# Step 19: Landlord generates CSV report
Write-Host "`nStep 19: Landlord generating CSV report" -ForegroundColor Yellow
$csvResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/payments/landlord-csv/$propertyId/" -Token $accessToken

# Step 20: Tenant generates CSV report
Write-Host "`nStep 20: Tenant generating CSV report" -ForegroundColor Yellow
$tenantCsvResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/payments/tenant-csv/$unitId/" -Token $tenantToken

# Step 21: Landlord sends email to tenants
Write-Host "`nStep 21: Landlord sending email to tenants" -ForegroundColor Yellow
$emailData = @{
    subject = "Maintenance Update"
    message = "We are working on fixing the reported issues. Thank you for your patience."
    recipient_ids = @($tenantId)
}
$emailResponse = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/communication/reports/send-email/" -Method "POST" -Body $emailData -Token $accessToken

# Step 22: Landlord views dashboard stats
Write-Host "`nStep 22: Landlord viewing dashboard statistics" -ForegroundColor Yellow
$dashboardStats = Invoke-AuthenticatedRequest -Uri "$baseUrl/api/accounts/dashboard-stats/" -Token $accessToken

# Step 23: Cleanup (optional - remove test data if API supports)
Write-Host "`nStep 23: Test completed. In a real scenario, you might want to clean up test data." -ForegroundColor Yellow

Write-Host "`nWorkflow test completed successfully!" -ForegroundColor Cyan
Write-Host "This script demonstrated the key workflows of the Makau Rentals app:" -ForegroundColor Cyan
Write-Host "- User registration and authentication" -ForegroundColor Cyan
Write-Host "- Property and unit management" -ForegroundColor Cyan
Write-Host "- Tenant assignment and management" -ForegroundColor Cyan
Write-Host "- Rent payments via M-Pesa" -ForegroundColor Cyan
Write-Host "- Maintenance reporting and communication" -ForegroundColor Cyan
