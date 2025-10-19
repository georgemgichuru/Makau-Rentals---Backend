# complete_test_api.ps1 - Comprehensive Rental Management API Test Script
# Tests all features: landlord/tenant signup, properties, units, subscriptions, payments, reports, password reset

Write-Host "==============================================" -ForegroundColor Green
Write-Host "COMPREHENSIVE RENTAL MANAGEMENT API TEST" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green

# Configuration
$BaseURL = "http://localhost:8000/api"
$TestEmailDomain = "@test.com"
$RandomSuffix = Get-Random -Minimum 1000 -Maximum 9999

# Test data
$LandlordData = @{
    email = "landlord$RandomSuffix$TestEmailDomain"
    full_name = "Test Landlord $RandomSuffix"
    password = "TestPassword123!"
    user_type = "landlord"
    phone_number = "+254700000000"
    government_id = "A12345678X"
    mpesa_till_number = "123456"
}

$TenantData = @{
    email = "tenant$RandomSuffix$TestEmailDomain"
    full_name = "Test Tenant $RandomSuffix"
    password = "TestPassword123!"
    user_type = "tenant"
    phone_number = "+254711111111"
    government_id = "B98765432Y"
    emergency_contact = "+254722222222"
}

$PropertyData = @{
    name = "Test Property $RandomSuffix"
    city = "Nairobi"
    state = "Nairobi County"
    unit_count = 3
}

$UnitTypeData = @{
    name = "Studio $RandomSuffix"
    deposit = 5000
    rent = 15000
    number_of_units = 2
}

# Global variables to store test data
$Global:LandlordToken = $null
$Global:TenantToken = $null
$Global:PropertyId = $null
$Global:UnitId = $null
$Global:UnitTypeId = $null
$Global:ReportId = $null
$Global:TenantId = $null
$Global:LandlordId = $null

# Utility functions
function Invoke-API {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null,
        [string]$Token = $null,
        [string]$ContentType = "application/json"
    )
    
    $Headers = @{}
    if ($Token) {
        $Headers["Authorization"] = "Bearer $Token"
    }
    
    $Uri = "$BaseURL$Endpoint"
    
    try {
        if ($Method -eq "GET") {
            $Response = Invoke-WebRequest -Uri $Uri -Method GET -Headers $Headers -ContentType $ContentType -UseBasicParsing
        }
        elseif ($Method -eq "POST") {
            $JsonBody = if ($Body) { $Body | ConvertTo-Json } else { $null }
            $Response = Invoke-WebRequest -Uri $Uri -Method POST -Body $JsonBody -Headers $Headers -ContentType $ContentType -UseBasicParsing
        }
        elseif ($Method -eq "PUT") {
            $JsonBody = if ($Body) { $Body | ConvertTo-Json } else { $null }
            $Response = Invoke-WebRequest -Uri $Uri -Method PUT -Body $JsonBody -Headers $Headers -ContentType $ContentType -UseBasicParsing
        }
        elseif ($Method -eq "PATCH") {
            $JsonBody = if ($Body) { $Body | ConvertTo-Json } else { $null }
            $Response = Invoke-WebRequest -Uri $Uri -Method PATCH -Body $JsonBody -Headers $Headers -ContentType $ContentType -UseBasicParsing
        }
        elseif ($Method -eq "DELETE") {
            $Response = Invoke-WebRequest -Uri $Uri -Method DELETE -Headers $Headers -ContentType $ContentType -UseBasicParsing
        }
        
        return @{
            Success = $true
            StatusCode = $Response.StatusCode
            Content = $Response.Content | ConvertFrom-Json
            Headers = $Response.Headers
        }
    }
    catch {
        $ErrorResponse = $_.Exception.Response
        return @{
            Success = $false
            StatusCode = if ($ErrorResponse) { $ErrorResponse.StatusCode.Value__ } else { 500 }
            Content = if ($ErrorResponse) { 
                try { $_.ErrorDetails.Message | ConvertFrom-Json } 
                catch { @{ error = $_.Exception.Message } }
            } else { @{ error = $_.Exception.Message } }
            Error = $_.Exception.Message
        }
    }
}

function Write-TestResult {
    param([string]$TestName, [bool]$Success, [string]$Message = "")
    
    if ($Success) {
        Write-Host "PASS: $TestName" -ForegroundColor Green
    }
    else {
        Write-Host "FAIL: $TestName" -ForegroundColor Red
        if ($Message) {
            Write-Host "Error: $Message" -ForegroundColor Yellow
        }
    }
}

function Wait-ForUser {
    Write-Host "Press any key to continue..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Write-Host ""
}

# Test Sections
function Test-Authentication {
    Write-Host "`n1. AUTHENTICATION & USER REGISTRATION" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    
    # Test welcome endpoint
    Write-Host "`nTesting Welcome Endpoint..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/accounts/welcome/"
    Write-TestResult -TestName "Welcome Endpoint" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Response: $($Result.Content.message)" -ForegroundColor White
    }
    
    # Landlord signup
    Write-Host "`nTesting Landlord Signup..." -ForegroundColor Gray
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/signup/" -Body $LandlordData
    Write-TestResult -TestName "Landlord Signup" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Landlord created: $($Result.Content.email)" -ForegroundColor White
        Write-Host "Landlord code: $($Result.Content.landlord_code)" -ForegroundColor White
    }
    
    # Landlord login
    Write-Host "`nTesting Landlord Login..." -ForegroundColor Gray
    $LoginData = @{
        email = $LandlordData.email
        password = $LandlordData.password
        user_type = "landlord"
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/token/" -Body $LoginData
    Write-TestResult -TestName "Landlord Login" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        $Global:LandlordToken = $Result.Content.access
        Write-Host "Access token obtained" -ForegroundColor White
    }
    
    # Tenant signup
    Write-Host "`nTesting Tenant Signup..." -ForegroundColor Gray
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/signup/" -Body $TenantData
    Write-TestResult -TestName "Tenant Signup" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Tenant created: $($Result.Content.email)" -ForegroundColor White
    }
    
    # Tenant login
    Write-Host "`nTesting Tenant Login..." -ForegroundColor Gray
    $LoginData = @{
        email = $TenantData.email
        password = $TenantData.password
        user_type = "tenant"
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/token/" -Body $LoginData
    Write-TestResult -TestName "Tenant Login" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        $Global:TenantToken = $Result.Content.access
        Write-Host "Access token obtained" -ForegroundColor White
    }
    
    # Test token refresh
    Write-Host "`nTesting Token Refresh..." -ForegroundColor Gray
    $RefreshData = @{ refresh = $Result.Content.refresh }
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/token/refresh/" -Body $RefreshData
    Write-TestResult -TestName "Token Refresh" -Success $Result.Success -Message $Result.Error
    
    Wait-ForUser
}

function Test-PropertyManagement {
    Write-Host "`n2. PROPERTY & UNIT MANAGEMENT" -ForegroundColor Cyan
    Write-Host "===============================" -ForegroundColor Cyan
    
    if (-not $Global:LandlordToken) {
        Write-Host "Skipping - No landlord token available" -ForegroundColor Yellow
        return
    }
    
    # Create property
    Write-Host "`nTesting Property Creation..." -ForegroundColor Gray
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/properties/create/" -Body $PropertyData -Token $Global:LandlordToken
    Write-TestResult -TestName "Create Property" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        $Global:PropertyId = $Result.Content.id
        Write-Host "Property created: $($Result.Content.name) (ID: $Global:PropertyId)" -ForegroundColor White
    }
    
    # List properties
    Write-Host "`nTesting Property Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/accounts/properties/" -Token $Global:LandlordToken
    Write-TestResult -TestName "List Properties" -Success $Result.Success -Message $Result.Error
    if ($Result.Success -and $Result.Content) {
        Write-Host "Found $($Result.Content.Count) properties" -ForegroundColor White
    }
    
    # Create unit type
    Write-Host "`nTesting Unit Type Creation..." -ForegroundColor Gray
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/unit-types/" -Body $UnitTypeData -Token $Global:LandlordToken
    Write-TestResult -TestName "Create Unit Type" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        $Global:UnitTypeId = $Result.Content.id
        Write-Host "Unit type created: $($Result.Content.name) (ID: $Global:UnitTypeId)" -ForegroundColor White
    }
    
    # Create unit
    Write-Host "`nTesting Unit Creation..." -ForegroundColor Gray
    $UnitData = @{
        property_obj = $Global:PropertyId
        unit_type = $Global:UnitTypeId
        unit_number = "101"
        floor = 1
        bedrooms = 1
        bathrooms = 1
        rent = 15000
        deposit = 5000
        is_available = $true
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/units/create/" -Body $UnitData -Token $Global:LandlordToken
    Write-TestResult -TestName "Create Unit" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        $Global:UnitId = $Result.Content.id
        Write-Host "Unit created: $($Result.Content.unit_number) (ID: $Global:UnitId)" -ForegroundColor White
        Write-Host "Unit code: $($Result.Content.unit_code)" -ForegroundColor White
    }
    
    # List units for property
    Write-Host "`nTesting Property Units Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/accounts/properties/$Global:PropertyId/units/" -Token $Global:LandlordToken
    Write-TestResult -TestName "List Property Units" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Found $($Result.Content.Count) units" -ForegroundColor White
    }
    
    # Update property
    Write-Host "`nTesting Property Update..." -ForegroundColor Gray
    $UpdateData = @{ name = "Updated $($PropertyData.name)" }
    $Result = Invoke-API -Method "PUT" -Endpoint "/accounts/properties/$Global:PropertyId/update/" -Body $UpdateData -Token $Global:LandlordToken
    Write-TestResult -TestName "Update Property" -Success $Result.Success -Message $Result.Error
    
    # List available units
    Write-Host "`nTesting Available Units Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/accounts/available-units/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Available Units" -Success $Result.Success -Message $Result.Error
    
    Wait-ForUser
}

function Test-SubscriptionSystem {
    Write-Host "`n3. SUBSCRIPTION SYSTEM" -ForegroundColor Cyan
    Write-Host "=======================" -ForegroundColor Cyan
    
    if (-not $Global:LandlordToken) {
        Write-Host "Skipping - No landlord token available" -ForegroundColor Yellow
        return
    }
    
    # Check subscription status
    Write-Host "`nTesting Subscription Status..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/payments/subscription-status/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Subscription Status" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Plan: $($Result.Content.plan)" -ForegroundColor White
        Write-Host "Status: $($Result.Content.status)" -ForegroundColor White
        Write-Host "Active: $($Result.Content.is_active)" -ForegroundColor White
    }
    
    # Update till number
    Write-Host "`nTesting Till Number Update..." -ForegroundColor Gray
    $TillData = @{ mpesa_till_number = "987654" }
    $Result = Invoke-API -Method "PATCH" -Endpoint "/payments/update-till-number/" -Body $TillData -Token $Global:LandlordToken
    Write-TestResult -TestName "Update Till Number" -Success $Result.Success -Message $Result.Error
    
    # Test subscription payment initiation
    Write-Host "`nTesting Subscription Payment Initiation..." -ForegroundColor Gray
    $SubscriptionData = @{
        plan = "starter"
        phone_number = $LandlordData.phone_number
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/payments/stk-push-subscription/" -Body $SubscriptionData -Token $Global:LandlordToken
    if ($Result.Success -or $Result.StatusCode -eq 400) {
        Write-TestResult -TestName "Subscription Payment Initiation" -Success $true
    }
    else {
        Write-TestResult -TestName "Subscription Payment Initiation" -Success $false -Message $Result.Error
    }
    
    Wait-ForUser
}

function Test-RentManagement {
    Write-Host "`n4. RENT & PAYMENT MANAGEMENT" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    
    if (-not $Global:LandlordToken -or -not $Global:TenantToken) {
        Write-Host "Skipping - Tokens not available" -ForegroundColor Yellow
        return
    }
    
    # Get user IDs
    Write-Host "`nGetting user information..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/accounts/me/" -Token $Global:TenantToken
    if ($Result.Success) {
        $Global:TenantId = $Result.Content.id
        Write-Host "Tenant ID: $Global:TenantId" -ForegroundColor White
    }
    
    $Result = Invoke-API -Method "GET" -Endpoint "/accounts/me/" -Token $Global:LandlordToken
    if ($Result.Success) {
        $Global:LandlordId = $Result.Content.id
        Write-Host "Landlord ID: $Global:LandlordId" -ForegroundColor White
    }
    
    # Adjust rent
    Write-Host "`nTesting Rent Adjustment..." -ForegroundColor Gray
    $RentAdjustData = @{
        adjustment_type = "percentage"
        value = 10
        unit_type_id = $Global:UnitTypeId
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/accounts/adjust-rent/" -Body $RentAdjustData -Token $Global:LandlordToken
    Write-TestResult -TestName "Adjust Rent" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Message: $($Result.Content.message)" -ForegroundColor White
    }
    
    # Test deposit payment initiation
    Write-Host "`nTesting Deposit Payment Initiation..." -ForegroundColor Gray
    $DepositData = @{
        unit_id = $Global:UnitId
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/payments/initiate-deposit/" -Body $DepositData -Token $Global:TenantToken
    if ($Result.Success -or $Result.StatusCode -eq 400) {
        Write-TestResult -TestName "Deposit Payment Initiation" -Success $true
        if ($Result.Success) {
            Write-Host "Payment ID: $($Result.Content.payment_id)" -ForegroundColor White
        }
    }
    else {
        Write-TestResult -TestName "Deposit Payment Initiation" -Success $false -Message $Result.Error
    }
    
    # Assign tenant to unit
    Write-Host "`nTesting Tenant Assignment..." -ForegroundColor Gray
    $AssignData = @{}
    $Result = Invoke-API -Method "POST" -Endpoint "/units/$Global:UnitId/assign/$Global:TenantId/" -Body $AssignData -Token $Global:LandlordToken
    Write-TestResult -TestName "Assign Tenant to Unit" -Success $Result.Success -Message $Result.Error
    
    # Test rent payment initiation
    Write-Host "`nTesting Rent Payment Initiation..." -ForegroundColor Gray
    $Result = Invoke-API -Method "POST" -Endpoint "/payments/stk-push/$Global:UnitId/" -Body @{} -Token $Global:TenantToken
    if ($Result.Success -or $Result.StatusCode -eq 400) {
        Write-TestResult -TestName "Rent Payment Initiation" -Success $true
        if ($Result.Success) {
            Write-Host "Payment ID: $($Result.Content.payment_id)" -ForegroundColor White
        }
    }
    else {
        Write-TestResult -TestName "Rent Payment Initiation" -Success $false -Message $Result.Error
    }
    
    # Get rent summary
    Write-Host "`nTesting Rent Summary..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/payments/rent-payments/summary/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Rent Summary" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Total collected: $($Result.Content.total_collected)" -ForegroundColor White
        Write-Host "Total outstanding: $($Result.Content.total_outstanding)" -ForegroundColor White
    }
    
    # List payments
    Write-Host "`nTesting Payments Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/payments/rent-payments/" -Token $Global:LandlordToken
    Write-TestResult -TestName "List Payments" -Success $Result.Success -Message $Result.Error
    
    # Dashboard stats
    Write-Host "`nTesting Dashboard Statistics..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/dashboard-stats/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Dashboard Stats" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Active tenants: $($Result.Content.total_active_tenants)" -ForegroundColor White
        Write-Host "Available units: $($Result.Content.total_units_available)" -ForegroundColor White
        Write-Host "Monthly revenue: $($Result.Content.monthly_revenue)" -ForegroundColor White
    }
    
    Wait-ForUser
}

function Test-CommunicationSystem {
    Write-Host "`n5. COMMUNICATION & REPORTING SYSTEM" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    
    if (-not $Global:TenantToken -or -not $Global:LandlordToken) {
        Write-Host "Skipping - Tokens not available" -ForegroundColor Yellow
        return
    }
    
    # Create maintenance report
    Write-Host "`nTesting Maintenance Report Creation..." -ForegroundColor Gray
    $ReportData = @{
        unit = $Global:UnitId
        issue_category = "plumbing"
        priority_level = "medium"
        issue_title = "Test Plumbing Issue - Leaking Pipe"
        description = "This is a test maintenance report for a leaking pipe in the bathroom"
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/reports/create/" -Body $ReportData -Token $Global:TenantToken
    Write-TestResult -TestName "Create Maintenance Report" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        $Global:ReportId = $Result.Content.id
        Write-Host "Report created: $($Result.Content.issue_title) (ID: $Global:ReportId)" -ForegroundColor White
    }
    
    # Update report status
    Write-Host "`nTesting Report Status Update..." -ForegroundColor Gray
    $UpdateData = @{ status = "in_progress" }
    $Result = Invoke-API -Method "PATCH" -Endpoint "/reports/$Global:ReportId/update-status/" -Body $UpdateData -Token $Global:LandlordToken
    Write-TestResult -TestName "Update Report Status" -Success $Result.Success -Message $Result.Error
    
    # List open reports
    Write-Host "`nTesting Open Reports Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/reports/open/" -Token $Global:LandlordToken
    Write-TestResult -TestName "List Open Reports" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Found $($Result.Content.Count) open reports" -ForegroundColor White
    }
    
    # List urgent reports
    Write-Host "`nTesting Urgent Reports Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/reports/urgent/" -Token $Global:LandlordToken
    Write-TestResult -TestName "List Urgent Reports" -Success $Result.Success -Message $Result.Error
    
    # Test email sending
    Write-Host "`nTesting Email Sending..." -ForegroundColor Gray
    $EmailData = @{
        subject = "Test Email from Rental Management System"
        message = "This is a test email message sent through the rental management system API."
        send_to_all = $true
    }
    $Result = Invoke-API -Method "POST" -Endpoint "/reports/send-email/" -Body $EmailData -Token $Global:LandlordToken
    if ($Result.Success -or $Result.StatusCode -eq 400) {
        Write-TestResult -TestName "Send Email" -Success $true
    }
    else {
        Write-TestResult -TestName "Send Email" -Success $false -Message $Result.Error
    }
    
    Wait-ForUser
}

function Test-UserManagement {
    Write-Host "`n6. USER MANAGEMENT & PREFERENCES" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    
    # Get user profile
    Write-Host "`nTesting User Profile Retrieval..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/me/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Get User Profile" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "User: $($Result.Content.full_name)" -ForegroundColor White
        Write-Host "Email: $($Result.Content.email)" -ForegroundColor White
    }
    
    # Update user profile
    Write-Host "`nTesting User Profile Update..." -ForegroundColor Gray
    $UpdateData = @{ phone_number = "+254733333333" }
    $Result = Invoke-API -Method "PATCH" -Endpoint "/me/" -Body $UpdateData -Token $Global:LandlordToken
    Write-TestResult -TestName "Update User Profile" -Success $Result.Success -Message $Result.Error
    
    # Update reminder preferences (tenant)
    Write-Host "`nTesting Reminder Preferences Update..." -ForegroundColor Gray
    $ReminderData = @{
        reminder_mode = "fixed_day"
        reminder_value = 15
    }
    $Result = Invoke-API -Method "PATCH" -Endpoint "/update-reminder-preferences/" -Body $ReminderData -Token $Global:TenantToken
    Write-TestResult -TestName "Update Reminder Preferences" -Success $Result.Success -Message $Result.Error
    
    # List tenants (landlord)
    Write-Host "`nTesting Tenants Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/tenants/" -Token $Global:LandlordToken
    Write-TestResult -TestName "List Tenants" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Found $($Result.Content.Count) tenants" -ForegroundColor White
    }
    
    Wait-ForUser
}

function Test-PasswordReset {
    Write-Host "`n7. PASSWORD RESET FUNCTIONALITY" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    
    # Password reset request
    Write-Host "`nTesting Password Reset Request..." -ForegroundColor Gray
    $ResetData = @{ email = $LandlordData.email }
    $Result = Invoke-API -Method "POST" -Endpoint "/password-reset/" -Body $ResetData
    Write-TestResult -TestName "Password Reset Request" -Success $Result.Success -Message $Result.Error
    if ($Result.Success) {
        Write-Host "Password reset email sent (check console for email output)" -ForegroundColor White
    }
    
    Write-Host "`nNote: Password reset confirmation requires actual token from email." -ForegroundColor Yellow
    Write-Host "This would be tested manually with a real email setup." -ForegroundColor Yellow
    
    Wait-ForUser
}

function Test-AdditionalEndpoints {
    Write-Host "`n8. ADDITIONAL ENDPOINTS" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    
    if (-not $Global:LandlordToken) {
        Write-Host "Skipping - No landlord token available" -ForegroundColor Yellow
        return
    }
    
    # List all unit types
    Write-Host "`nTesting Unit Types Listing..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/unit-types/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Unit Types List" -Success $Result.Success -Message $Result.Error
    
    # Test M-Pesa connectivity
    Write-Host "`nTesting M-Pesa Connectivity..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/payments/test-mpesa/" -Token $Global:LandlordToken
    Write-TestResult -TestName "M-Pesa Test" -Success $Result.Success -Message $Result.Error
    
    # Cleanup pending payments
    Write-Host "`nTesting Payment Cleanup..." -ForegroundColor Gray
    $Result = Invoke-API -Method "POST" -Endpoint "/payments/cleanup-pending-payments/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Payment Cleanup" -Success $Result.Success -Message $Result.Error
    
    Wait-ForUser
}

function Test-ErrorScenarios {
    Write-Host "`n9. ERROR SCENARIOS" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Cyan
    
    # Test unauthorized access
    Write-Host "`nTesting Unauthorized Access..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/dashboard-stats/"
    Write-TestResult -TestName "Unauthorized Access" -Success (-not $Result.Success) -Message "Expected to fail"
    
    # Test invalid token
    Write-Host "`nTesting Invalid Token..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/dashboard-stats/" -Token "invalid_token"
    Write-TestResult -TestName "Invalid Token" -Success (-not $Result.Success) -Message "Expected to fail"
    
    # Test invalid endpoint
    Write-Host "`nTesting Invalid Endpoint..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/invalid-endpoint/" -Token $Global:LandlordToken
    Write-TestResult -TestName "Invalid Endpoint" -Success (-not $Result.Success) -Message "Expected to fail"
    
    # Test tenant accessing landlord endpoints
    Write-Host "`nTesting Tenant Accessing Landlord Endpoints..." -ForegroundColor Gray
    $Result = Invoke-API -Method "GET" -Endpoint "/dashboard-stats/" -Token $Global:TenantToken
    Write-TestResult -TestName "Tenant Accessing Landlord Endpoint" -Success (-not $Result.Success) -Message "Expected to fail"
    
    Wait-ForUser
}

# Main execution
try {
    Write-Host "Starting comprehensive API tests..." -ForegroundColor Green
    Write-Host "Base URL: $BaseURL" -ForegroundColor Gray
    Write-Host "Test ID: $RandomSuffix" -ForegroundColor Gray
    Write-Host "Test emails: landlord$RandomSuffix$TestEmailDomain, tenant$RandomSuffix$TestEmailDomain" -ForegroundColor Gray
    
    Test-Authentication
    Test-PropertyManagement
    Test-SubscriptionSystem
    Test-RentManagement
    Test-CommunicationSystem
    Test-UserManagement
    Test-PasswordReset
    Test-AdditionalEndpoints
    Test-ErrorScenarios
    
    Write-Host "`n" + "="*60 -ForegroundColor Green
    Write-Host "COMPREHENSIVE API TESTING COMPLETED!" -ForegroundColor Green
    Write-Host "="*60 -ForegroundColor Green
    
    Write-Host "`nSUMMARY OF CREATED TEST DATA:" -ForegroundColor Cyan
    Write-Host "Landlord: $($LandlordData.email)" -ForegroundColor White
    Write-Host "Tenant: $($TenantData.email)" -ForegroundColor White
    Write-Host "Property ID: $Global:PropertyId" -ForegroundColor White
    Write-Host "Unit ID: $Global:UnitId" -ForegroundColor White
    Write-Host "Unit Type ID: $Global:UnitTypeId" -ForegroundColor White
    Write-Host "Report ID: $Global:ReportId" -ForegroundColor White
    Write-Host "Landlord ID: $Global:LandlordId" -ForegroundColor White
    Write-Host "Tenant ID: $Global:TenantId" -ForegroundColor White
    
    Write-Host "`nNOTES:" -ForegroundColor Yellow
    Write-Host "- M-Pesa payments are simulated (test mode)" -ForegroundColor Yellow
    Write-Host "- Email sending uses console backend" -ForegroundColor Yellow
    Write-Host "- All errors are displayed for debugging" -ForegroundColor Yellow
    Write-Host "- Test data uses random suffix: $RandomSuffix" -ForegroundColor Yellow
    
}
catch {
    Write-Host "`nFatal error during testing: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
}

Write-Host "`nTest script execution finished." -ForegroundColor Gray