# Comprehensive test script v2 for Makau Rentals backend flows - MINIMAL AMOUNTS
# Tests all endpoints in accounts, payments, and communication
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

# Function to perform PUT request with Authorization header
function Invoke-PutAuth {
    param (
        [string]$url,
        [string]$token,
        [string]$body
    )
    $headers = @{ Authorization = "Bearer $token" }
    try {
        return Invoke-RestMethod -Uri $url -Method PUT -Headers $headers -Body $body -ContentType "application/json"
    } catch {
        Write-Host "Error in PUT to $url`: $($_.Exception.Message)"
        throw
    }
}

# Function to perform PATCH request with Authorization header
function Invoke-PatchAuth {
    param (
        [string]$url,
        [string]$token,
        [string]$body
    )
    $headers = @{ Authorization = "Bearer $token" }
    try {
        return Invoke-RestMethod -Uri $url -Method PATCH -Headers $headers -Body $body -ContentType "application/json"
    } catch {
        Write-Host "Error in PATCH to $url`: $($_.Exception.Message)"
        throw
    }
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
$tenantPhone = "254722714334"

# 1. Signup Landlord (no properties)
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

# 2.1. Test token refresh
Write-Host "2.1. Refreshing token..."
$refreshBody = @{
    refresh = $landlordLoginResponse.refresh
} | ConvertTo-Json

$refreshResponse = Invoke-PostJson -url "$baseUrl/api/accounts/token/refresh/" -body $refreshBody
Write-Host "Token refreshed successfully."
$landlordToken = $refreshResponse.access

# 2.2. Test /me/ endpoint
Write-Host "2.2. Getting current user info..."
$meResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/me/" -token $landlordToken
Write-Host "Current user: $($meResponse | ConvertTo-Json)"

# 2.3. Test subscription_status/
Write-Host "2.3. Getting subscription status..."
$statusResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/subscription-status/" -token $landlordToken
Write-Host "Subscription status: $($statusResponse | ConvertTo-Json)"

# 3. Create Property as Landlord
Write-Host "3. Creating property..."
$propertyBody = @{
    name = "Test Property"
    city = "Nairobi"
    state = "Kenya"
    unit_count = 1
} | ConvertTo-Json

$propertyHeaders = @{ Authorization = "Bearer $landlordToken" }
$propertyResponse = Invoke-PostJson -url "$baseUrl/api/accounts/properties/create/" -headers $propertyHeaders -body $propertyBody
Write-Host "Property created. ID: $($propertyResponse.id)"
$propertyId = $propertyResponse.id

# 4. Create UnitType as Landlord with MINIMAL amounts
Write-Host "4. Creating unit type with minimal amounts (10 KSH deposit, 100 KSH rent)..."
$unitTypeBody = @{
    name = "1 Bedroom Minimal"
    deposit = 10    # Only 10 KSH for testing
    rent = 100      # Only 100 KSH rent for testing
    unit_count = 2
    property_id = $propertyId
} | ConvertTo-Json

$unitTypeResponse = Invoke-PostJson -url "$baseUrl/api/accounts/unit-types/" -headers $propertyHeaders -body $unitTypeBody
Write-Host "Unit type created. ID: $($unitTypeResponse.id)"
$unitTypeId = $unitTypeResponse.id
$unitDeposit = 10  # Only 10 KSH deposit
$unitRent = 100    # Only 100 KSH rent

# 5. List Units to verify automatic creation
Write-Host "5. Listing units..."
$unitsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/properties/$propertyId/units/" -token $landlordToken
Write-Host "Units created: $($unitsResponse.count) units"
$unitId = $unitsResponse[0].id
$unitCode = $unitsResponse[0].unit_code
Write-Host "First unit ID: $unitId, Code: $unitCode"

# 5.1. Test available-units/
Write-Host "5.1. Listing available units..."
$availableResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/available-units/" -token $landlordToken
Write-Host "Available units: $($availableResponse | ConvertTo-Json)"

# 5.2. Test dashboard-stats/
Write-Host "5.2. Getting dashboard stats..."
$statsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/dashboard-stats/" -token $landlordToken
Write-Host "Dashboard stats: $($statsResponse | ConvertTo-Json)"

# 6. Signup Tenant (with landlord_code, no unit_code to skip deposit check)
Write-Host "6. Signing up tenant..."
$tenantSignupBody = @{
    email = $tenantEmail
    full_name = $tenantFullName
    user_type = "tenant"
    password = $tenantPassword
    phone_number = $tenantPhone
    landlord_code = $landlordCode
    # No unit_code to avoid deposit requirement
} | ConvertTo-Json

$tenantSignupResponse = Invoke-PostJson -url "$baseUrl/api/accounts/signup/" -body $tenantSignupBody
Write-Host "Tenant signup successful. ID: $($tenantSignupResponse.id)"
$tenantId = $tenantSignupResponse.id

# 7. Login Tenant
Write-Host "7. Logging in tenant..."
$tenantLoginBody = @{
    email = $tenantEmail
    password = $tenantPassword
    user_type = "tenant"
} | ConvertTo-Json

$tenantLoginResponse = Invoke-PostJson -url "$baseUrl/api/accounts/token/" -body $tenantLoginBody
Write-Host "Tenant login successful."
$tenantToken = $tenantLoginResponse.access
$tenantHeaders = @{ Authorization = "Bearer $tenantToken" }

# 7.1. Test update-reminder-preferences/
Write-Host "7.1. Updating reminder preferences..."
$reminderBody = @{
    rent_reminder = $true
    maintenance_reminder = $true
} | ConvertTo-Json

$reminderResponse = Invoke-PatchAuth -url "$baseUrl/api/accounts/update-reminder-preferences/" -token $tenantToken -body $reminderBody
Write-Host "Reminder preferences updated: $($reminderResponse | ConvertTo-Json)"

# 8.1. Test deposit check before assignment: Try to assign tenant without successful deposit (should fail)
Write-Host "8.1. Attempting to assign tenant without deposit (should fail)..."
$assignBody = @{} | ConvertTo-Json
try {
    $failedAssignResponse = Invoke-PostJson -url "$baseUrl/api/accounts/units/$unitId/assign/$tenantId/" -headers $propertyHeaders -body $assignBody
    Write-Host "ERROR: Assignment succeeded unexpectedly without deposit!"
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "SUCCESS: Assignment correctly failed due to missing deposit: $($_.Exception.Message)"
    } else {
        Write-Host "Unexpected error during assignment attempt: $($_.Exception.Message)"
    }
}

# 8.2. Initiate Deposit Payment as Tenant (only 10 KSH)
Write-Host "8.2. Initiating deposit payment (10 KSH only)..."
$depositBody = @"
{
    "unit_id": $unitId
}
"@

$depositHeaders = @{ Authorization = "Bearer $tenantToken" }
$startTime = Get-Date
Write-Host "Deposit initiation started at: $startTime"
try {
    $depositResponse = Invoke-PostJson -url "$baseUrl/api/payments/initiate-deposit/" -headers $depositHeaders -body $depositBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Deposit STK push initiated in $($duration.TotalSeconds) seconds: $($depositResponse | ConvertTo-Json)"
    if ($duration.TotalSeconds -ge 25 -and $duration.TotalSeconds -le 35) {
        Write-Host "SUCCESS: Deposit initiation waited approximately 30 seconds (timeout scenario)"
    } elseif ($duration.TotalSeconds -lt 5) {
        Write-Host "SUCCESS: Deposit initiation returned quickly (success scenario)"
    } else {
        Write-Host "WARNING: Unexpected duration for deposit initiation"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Deposit initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
    if ($duration.TotalSeconds -ge 25 -and $duration.TotalSeconds -le 35) {
        Write-Host "SUCCESS: Deposit initiation waited approximately 30 seconds before failing"
    }
}

# 8.3. Simulate successful deposit callback for testing (10 KSH)
Write-Host "8.3. Simulating successful deposit callback (10 KSH)..."
# Get the pending deposit payment
Start-Sleep -Seconds 2  # Wait for payment to be created
$paymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-payments/" -token $tenantToken
if ($paymentsResponse.results) {
    $depositPayment = $paymentsResponse.results | Where-Object { $_.payment_type -eq "deposit" -and $_.status -eq "Pending" } | Select-Object -First 1
} else {
    $depositPayment = $paymentsResponse | Where-Object { $_.payment_type -eq "deposit" -and $_.status -eq "Pending" } | Select-Object -First 1
}

if ($depositPayment) {
    $paymentId = $depositPayment.id
    Write-Host "Found pending deposit payment ID: $paymentId"
    # Simulate callback with correct amount (10 KSH deposit)
    $callbackBody = @"
{
    "Body": {
        "stkCallback": {
            "ResultCode": 0,
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 10},
                    {"Name": "MpesaReceiptNumber", "Value": "TEST$paymentId"},
                    {"Name": "AccountReference", "Value": "$paymentId"},
                    {"Name": "PhoneNumber", "Value": "$tenantPhone"}
                ]
            }
        }
    }
}
"@
    try {
        $callbackResponse = Invoke-PostJson -url "$baseUrl/api/payments/callback/deposit/" -body $callbackBody
        Write-Host "Deposit callback simulated successfully: $($callbackResponse | ConvertTo-Json)"
        
        # Verify payment status update
        Start-Sleep -Seconds 2  # Wait for callback processing
        $updatedPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-payments/" -token $tenantToken
        if ($updatedPaymentsResponse.results) {
            $updatedDepositPayment = $updatedPaymentsResponse.results | Where-Object { $_.id -eq $paymentId } | Select-Object -First 1
        } else {
            $updatedDepositPayment = $updatedPaymentsResponse | Where-Object { $_.id -eq $paymentId } | Select-Object -First 1
        }
        
        if ($updatedDepositPayment.status -eq "Success") {
            Write-Host "SUCCESS: Deposit payment status updated to Success"
            
            # Now try to assign tenant after successful deposit
            Write-Host "8.4. Attempting to assign tenant AFTER successful deposit..."
            $assignBody = @{} | ConvertTo-Json
            try {
                $assignResponse = Invoke-PostJson -url "$baseUrl/api/accounts/units/$unitId/assign/$tenantId/" -headers $propertyHeaders -body $assignBody
                Write-Host "SUCCESS: Tenant assigned to unit after deposit payment: $($assignResponse | ConvertTo-Json)"
            } catch {
                Write-Host "Assignment still failed after deposit: $($_.Exception.Message)"
            }
        } else {
            Write-Host "WARNING: Deposit payment status not updated to Success (current: $($updatedDepositPayment.status))"
        }
    } catch {
        Write-Host "Deposit callback simulation failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "No pending deposit payment found for callback simulation"
}

# 9. Initiate Rent Payment as Tenant (100 KSH)
Write-Host "9. Initiating rent payment (100 KSH)..."
$rentBody = @{
    amount = "100"
} | ConvertTo-Json

$startTime = Get-Date
Write-Host "Rent initiation started at: $startTime"
try {
    $rentResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push/$unitId/" -headers $depositHeaders -body $rentBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Rent STK push initiated in $($duration.TotalSeconds) seconds: $($rentResponse | ConvertTo-Json)"
    if ($duration.TotalSeconds -ge 25 -and $duration.TotalSeconds -le 35) {
        Write-Host "SUCCESS: Rent initiation waited approximately 30 seconds (timeout scenario)"
    } elseif ($duration.TotalSeconds -lt 5) {
        Write-Host "SUCCESS: Rent initiation returned quickly (success scenario)"
    } else {
        Write-Host "WARNING: Unexpected duration for rent initiation"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Rent initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
    if ($duration.TotalSeconds -ge 25 -and $duration.TotalSeconds -le 35) {
        Write-Host "SUCCESS: Rent initiation waited approximately 30 seconds before failing"
    }
}

# 9.1. Test rent-payments/ list
Write-Host "9.1. Listing rent payments..."
$rentPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-payments/" -token $tenantToken
Write-Host "Rent payments: $($rentPaymentsResponse | ConvertTo-Json)"

# 10. Create Report as Tenant
Write-Host "10. Creating report as tenant..."
$reportBody = @{
    unit = $unitId
    issue_title = "Test Report"
    issue_category = "maintenance"
    description = "This is a test report for maintenance."
    priority_level = "low"
} | ConvertTo-Json

$reportResponse = Invoke-PostJson -url "$baseUrl/api/communication/reports/create/" -headers $depositHeaders -body $reportBody
Write-Host "Report created. ID: $($reportResponse.id)"
$reportId = $reportResponse.id

# 11. Initiate Subscription Payment as Landlord (50 KSH test plan)
Write-Host "11. Initiating subscription payment (50 KSH test plan)..."
$subscriptionBody = @{
    plan = "starter"
    phone_number = $landlordPhone
} | ConvertTo-Json

$subscriptionHeaders = @{ Authorization = "Bearer $landlordToken" }
$startTime = Get-Date
Write-Host "Subscription initiation started at: $startTime"
try {
    $subscriptionResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push-subscription/" -headers $subscriptionHeaders -body $subscriptionBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Subscription STK push initiated in $($duration.TotalSeconds) seconds: $($subscriptionResponse | ConvertTo-Json)"
    if ($duration.TotalSeconds -ge 25 -and $duration.TotalSeconds -le 35) {
        Write-Host "SUCCESS: Subscription initiation waited approximately 30 seconds (timeout scenario)"
    } elseif ($duration.TotalSeconds -lt 5) {
        Write-Host "SUCCESS: Subscription initiation returned quickly (success scenario)"
    } else {
        Write-Host "WARNING: Unexpected duration for subscription initiation"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Subscription initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
    if ($duration.TotalSeconds -ge 25 -and $duration.TotalSeconds -le 35) {
        Write-Host "SUCCESS: Subscription initiation waited approximately 30 seconds before failing"
    }
}

# 11.1. Test subscription-payments/ list
Write-Host "11.1. Listing subscription payments..."
$subscriptionPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/subscription-payments/" -token $landlordToken
Write-Host "Subscription payments: $($subscriptionPaymentsResponse | ConvertTo-Json)"

Write-Host "All tests completed with minimal amounts (10 KSH deposit, 100 KSH rent, 50 KSH subscription)!"