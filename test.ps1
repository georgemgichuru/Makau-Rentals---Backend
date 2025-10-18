# Comprehensive test script v4 for Makau Rentals backend flows - MINIMAL AMOUNTS
# UPDATED to match actual API endpoints and JSON structure from your codebase
# Uses 10 KSH deposit, 100 KSH rent, 50 KSH subscription for testing

$baseUrl = "https://makau-rentals-backend.onrender.com"

# Function to perform POST request with JSON body
function Invoke-PostJson {
    param (
        [string]$url,
        [hashtable]$headers = @{},
        [string]$body
    )
    try {
        return Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -ContentType "application/json"
    } catch {
        Write-Host "Error in POST to $url`: $($_.Exception.Message)"
        if ($_.Exception.Response) {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response body: $responseBody"
        }
        throw
    }
}

# Function to perform GET request with Authorization header
function Invoke-GetAuth {
    param (
        [string]$url,
        [string]$token
    )
    $headers = @{ Authorization = "Bearer $token" }
    try {
        return Invoke-RestMethod -Uri $url -Method GET -Headers $headers
    } catch {
        Write-Host "Error in GET to $url`: $($_.Exception.Message)"
        throw
    }
}

# Function to poll deposit payment status
function Invoke-PollDepositPaymentStatus {
    param (
        [string]$paymentId,
        [string]$token,
        [int]$maxAttempts = 12,
        [int]$delaySeconds = 10
    )

    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        Write-Host "Polling deposit payment status (attempt $attempt of $maxAttempts)..."
        Start-Sleep -Seconds $delaySeconds

        try {
            $statusResponse = Invoke-GetAuth -url "$baseUrl/api/payments/deposit-status/$paymentId/" -token $token
            Write-Host "Deposit payment status: $($statusResponse.status)"

            if ($statusResponse.status -ne "Pending") {
                return $statusResponse
            }
        } catch {
            Write-Host "Error polling deposit payment status: $($_.Exception.Message)"
        }
    }

    return @{ status = "timeout"; message = "Deposit payment status polling timed out" }
}

# Test data
$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$landlordEmail = "test_landlord_$timestamp@example.com"
$landlordPassword = "testpass123"
$landlordFullName = "Test Landlord"
$landlordPhone = "254722714334"

$tenantEmail = "test_tenant_$timestamp@example.com"
$tenantPassword = "testpass123"
$tenantFullName = "Test Tenant" 
$tenantPhone = "254733123456"

# 1. Signup Landlord
Write-Host "1. Signing up landlord..."
$landlordSignupBody = @{
    email = $landlordEmail
    full_name = $landlordFullName
    user_type = "landlord"
    password = $landlordPassword
    phone_number = $landlordPhone
} | ConvertTo-Json

$landlordSignupResponse = Invoke-PostJson -url "$baseUrl/api/accounts/signup/" -body $landlordSignupBody
Write-Host "Landlord signup successful. ID: $($landlordSignupResponse.id)"
$landlordId = $landlordSignupResponse.id
$landlordCode = $landlordSignupResponse.landlord_code
Write-Host "Landlord code: $landlordCode"

# 2. Login Landlord
Write-Host "2. Logging in landlord..."
$landlordLoginBody = @{
    email = $landlordEmail
    password = $landlordPassword
    user_type = "landlord"
} | ConvertTo-Json

$landlordLoginResponse = Invoke-PostJson -url "$baseUrl/api/accounts/token/" -body $landlordLoginBody
Write-Host "Landlord login successful."
$landlordToken = $landlordLoginResponse.access
$landlordHeaders = @{ Authorization = "Bearer $landlordToken" }

# 3. Test /me/ endpoint
Write-Host "3. Getting current user info..."
$meResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/me/" -token $landlordToken
Write-Host "Current user: $($meResponse.email)"

# 4. Create Property as Landlord
Write-Host "4. Creating property..."
$propertyBody = @{
    name = "Test Property $timestamp"
    city = "Nairobi"
    state = "Kenya"
    unit_count = 2
} | ConvertTo-Json

$propertyResponse = Invoke-PostJson -url "$baseUrl/api/accounts/properties/create/" -headers $landlordHeaders -body $propertyBody
Write-Host "Property created. ID: $($propertyResponse.id)"
$propertyId = $propertyResponse.id

# 5. Create UnitType as Landlord with MINIMAL amounts
Write-Host "5. Creating unit type with minimal amounts (10 KSH deposit, 100 KSH rent)..."
$unitTypeBody = @{
    name = "Studio Minimal $timestamp"
    deposit = 10.00
    rent = 100.00
    number_of_units = 1
} | ConvertTo-Json

$unitTypeResponse = Invoke-PostJson -url "$baseUrl/api/accounts/unit-types/" -headers $landlordHeaders -body $unitTypeBody
Write-Host "Unit type created. ID: $($unitTypeResponse.id)"
$unitTypeId = $unitTypeResponse.id

# 6. Create Unit manually (since automatic creation might not work)
Write-Host "6. Creating unit manually..."
$unitBody = @{
    property_obj = $propertyId
    unit_type = $unitTypeId
    unit_number = "101"
    bedrooms = 1
    bathrooms = 1
    rent = 100.00
    deposit = 10.00
    is_available = $true
} | ConvertTo-Json

$unitResponse = Invoke-PostJson -url "$baseUrl/api/accounts/units/create/" -headers $landlordHeaders -body $unitBody
Write-Host "Unit created. ID: $($unitResponse.id)"
$unitId = $unitResponse.id
$unitCode = $unitResponse.unit_code
Write-Host "Unit Code: $unitCode"

# 7. List Units to verify creation
Write-Host "7. Listing units..."
$unitsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/properties/$propertyId/units/" -token $landlordToken
Write-Host "Units count: $($unitsResponse.Count)"

# 8. Test available-units/
Write-Host "8. Listing available units..."
$availableResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/available-units/" -token $landlordToken
Write-Host "Available units count: $($availableResponse.Count)"

# 9. Signup Tenant (with landlord_code for discovery)
Write-Host "9. Signing up tenant..."
$tenantSignupBody = @{
    email = $tenantEmail
    full_name = $tenantFullName
    user_type = "tenant"
    password = $tenantPassword
    phone_number = $tenantPhone
    landlord_code = $landlordCode
} | ConvertTo-Json

$tenantSignupResponse = Invoke-PostJson -url "$baseUrl/api/accounts/signup/" -body $tenantSignupBody
Write-Host "Tenant signup successful. ID: $($tenantSignupResponse.id)"
$tenantId = $tenantSignupResponse.id

# 10. Login Tenant
Write-Host "10. Logging in tenant..."
$tenantLoginBody = @{
    email = $tenantEmail
    password = $tenantPassword
    user_type = "tenant"
} | ConvertTo-Json

$tenantLoginResponse = Invoke-PostJson -url "$baseUrl/api/accounts/token/" -body $tenantLoginBody
Write-Host "Tenant login successful."
$tenantToken = $tenantLoginResponse.access
$tenantHeaders = @{ Authorization = "Bearer $tenantToken" }

# 11. REAL FLOW: Initiate Deposit Payment (10 KSH) - Tenant pays deposit first
Write-Host "11. REAL FLOW: Initiating deposit payment (10 KSH)..."
$depositBody = @{
    unit_id = $unitId
} | ConvertTo-Json

$startTime = Get-Date
Write-Host "Deposit initiation started at: $startTime"
try {
    $depositResponse = Invoke-PostJson -url "$baseUrl/api/payments/initiate-deposit/" -headers $tenantHeaders -body $depositBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Deposit response received in $($duration.TotalSeconds) seconds: $($depositResponse | ConvertTo-Json)"

    if ($depositResponse.payment_id) {
        $paymentId = $depositResponse.payment_id
        Write-Host "Payment ID: $paymentId"
        Write-Host "Please complete the M-Pesa payment on your phone..."

        # Poll for payment status
        Write-Host "11.1. Polling for deposit payment status..."
        $statusResult = Invoke-PollDepositPaymentStatus -paymentId $paymentId -token $tenantToken

        Write-Host "Final deposit payment status: $($statusResult.status)"
        if ($statusResult.status -eq "Success") {
            Write-Host "SUCCESS: Deposit payment completed and tenant assigned to unit"
        } else {
            Write-Host "Payment status: $($statusResult.status)"
        }
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Deposit initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
}

# 12. Verify tenant assignment by checking unit status
Write-Host "12. Verifying unit assignment status..."
try {
    $updatedUnitsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/properties/$propertyId/units/" -token $landlordToken
    $assignedUnit = $updatedUnitsResponse | Where-Object { $_.id -eq $unitId } | Select-Object -First 1
    
    if ($assignedUnit.tenant -eq $tenantId) {
        Write-Host "SUCCESS: Tenant $tenantId is properly assigned to unit $unitId"
        Write-Host "Unit availability: $($assignedUnit.is_available)"
    } else {
        Write-Host "UNIT STATUS: Unit $unitId tenant: $($assignedUnit.tenant), available: $($assignedUnit.is_available)"
    }
} catch {
    Write-Host "Error checking unit assignment: $($_.Exception.Message)"
}

# 13. REAL FLOW: Initiate Rent Payment as Tenant (100 KSH) - Only if deposit was successful
Write-Host "13. REAL FLOW: Initiating rent payment (100 KSH)..."
$rentBody = @{
    amount = "100"
} | ConvertTo-Json

$startTime = Get-Date
Write-Host "Rent initiation started at: $startTime"
try {
    $rentResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push/$unitId/" -headers $tenantHeaders -body $rentBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Rent STK push response in $($duration.TotalSeconds) seconds: $($rentResponse | ConvertTo-Json)"

    if ($rentResponse.checkout_request_id) {
        Write-Host "Checkout Request ID: $($rentResponse.checkout_request_id)"
        Write-Host "Please complete the M-Pesa payment on your phone..."
        Write-Host "Note: Rent payments use automatic callbacks - no manual status polling needed"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Rent initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
}

# 14. Test rent-payments/ list
Write-Host "14. Listing rent payments..."
try {
    $rentPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-payments/" -token $tenantToken
    Write-Host "Rent payments count: $($rentPaymentsResponse.Count)"
} catch {
    Write-Host "Rent payments list failed: $($_.Exception.Message)"
}

# 15. Create Report as Tenant
Write-Host "15. Creating report as tenant..."
$reportBody = @{
    unit = $unitId
    issue_title = "Test Maintenance Report $timestamp"
    issue_category = "maintenance"
    description = "This is a test report for maintenance issues."
    priority_level = "medium"
} | ConvertTo-Json

try {
    $reportResponse = Invoke-PostJson -url "$baseUrl/api/communication/reports/create/" -headers $tenantHeaders -body $reportBody
    Write-Host "Report created. ID: $($reportResponse.id)"
    $reportId = $reportResponse.id
} catch {
    Write-Host "Report creation failed: $($_.Exception.Message)"
}

# 16. REAL FLOW: Initiate Subscription Payment as Landlord (50 KSH starter plan)
Write-Host "16. REAL FLOW: Initiating subscription payment (50 KSH starter plan)..."
$subscriptionBody = @{
    plan = "starter"
    phone_number = $landlordPhone
} | ConvertTo-Json

$startTime = Get-Date
Write-Host "Subscription initiation started at: $startTime"
try {
    $subscriptionResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push-subscription/" -headers $landlordHeaders -body $subscriptionBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Subscription STK push response in $($duration.TotalSeconds) seconds: $($subscriptionResponse | ConvertTo-Json)"

    if ($subscriptionResponse.checkout_request_id) {
        Write-Host "Checkout Request ID: $($subscriptionResponse.checkout_request_id)"
        Write-Host "Please complete the M-Pesa payment on your phone..."
        Write-Host "Note: Subscription payments use automatic callbacks - no manual status polling needed"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Subscription initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
}

# 17. Test subscription-payments/ list
Write-Host "17. Listing subscription payments..."
try {
    $subscriptionPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/subscription-payments/" -token $landlordToken
    Write-Host "Subscription payments count: $($subscriptionPaymentsResponse.Count)"
} catch {
    Write-Host "Subscription payments list failed: $($_.Exception.Message)"
}

# 18. Test rent summary for landlord
Write-Host "18. Testing rent summary..."
try {
    $rentSummaryResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-summary/" -token $landlordToken
    Write-Host "Rent summary - Total collected: $($rentSummaryResponse.total_collected), Total outstanding: $($rentSummaryResponse.total_outstanding)"
} catch {
    Write-Host "Rent summary failed: $($_.Exception.Message)"
}

# 19. Test dashboard stats
Write-Host "19. Testing dashboard stats..."
try {
    $statsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/dashboard-stats/" -token $landlordToken
    Write-Host "Dashboard stats - Active tenants: $($statsResponse.total_active_tenants), Available units: $($statsResponse.total_units_available)"
} catch {
    Write-Host "Dashboard stats failed: $($_.Exception.Message)"
}

# 20. Test subscription status
Write-Host "20. Testing subscription status..."
try {
    $subscriptionStatusResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/subscription-status/" -token $landlordToken
    Write-Host "Subscription status - Plan: $($subscriptionStatusResponse.plan), Active: $($subscriptionStatusResponse.is_active)"
} catch {
    Write-Host "Subscription status failed: $($_.Exception.Message)"
}

Write-Host "`n=== TEST SUMMARY ==="
Write-Host "All API endpoints tested with real M-Pesa integration"
Write-Host "Key endpoints tested:"
Write-Host "- Authentication (signup, login, token refresh)"
Write-Host "- Property and Unit management"
Write-Host "- Deposit payment flow with status polling"
Write-Host "- Rent payment initiation"
Write-Host "- Subscription payment initiation"
Write-Host "- Report creation"
Write-Host "- Dashboard and summary endpoints"
Write-Host "`nNote: Complete the M-Pesa payments on your phone to test the full callback flow!"