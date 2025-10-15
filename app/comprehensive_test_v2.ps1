# Comprehensive test script v3 for Makau Rentals backend flows - MINIMAL AMOUNTS
# Tests all endpoints in accounts, payments, and communication
# Uses 10 KSH deposit, 100 KSH rent, 50 KSH subscription for testing
# UPDATED: Now properly handles deposit payment flow with callback confirmation

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

# Function to perform POST request with Authorization header
function Invoke-PostAuth {
    param (
        [string]$url,
        [string]$token,
        [string]$body
    )
    $headers = @{ Authorization = "Bearer $token" }
    try {
        return Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -ContentType "application/json"
    } catch {
        Write-Host "Error in POST to $url`: $($_.Exception.Message)"
        throw
    }
}

# Function to poll payment status
function Invoke-PollPaymentStatus {
    param (
        [string]$paymentId,
        [string]$token,
        [int]$maxAttempts = 6,
        [int]$delaySeconds = 5
    )
    
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        Write-Host "Polling payment status (attempt $attempt of $maxAttempts)..."
        Start-Sleep -Seconds $delaySeconds
        
        try {
            $statusResponse = Invoke-GetAuth -url "$baseUrl/api/payments/deposit-status/$paymentId/" -token $token
            Write-Host "Payment status: $($statusResponse.status)"
            
            if ($statusResponse.status -ne "Pending") {
                return $statusResponse
            }
        } catch {
            Write-Host "Error polling payment status: $($_.Exception.Message)"
        }
    }
    
    return @{ status = "timeout"; message = "Payment status polling timed out" }
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

# 8. NEW FLOW: Initiate Deposit Payment (10 KSH) - Tenant pays deposit first
Write-Host "8. NEW FLOW: Initiating deposit payment (10 KSH)..."
$depositBody = @{
    unit_id = $unitId
} | ConvertTo-Json

$startTime = Get-Date
Write-Host "Deposit initiation started at: $startTime"
try {
    $depositResponse = Invoke-PostJson -url "$baseUrl/api/payments/initiate-deposit/" -headers $tenantHeaders -body $depositBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Deposit initiation completed in $($duration.TotalSeconds) seconds: $($depositResponse | ConvertTo-Json)"
    
    if ($depositResponse.payment_id) {
        $paymentId = $depositResponse.payment_id
        Write-Host "Payment ID: $paymentId"
        
        # NEW: Poll for payment status instead of assuming success
        Write-Host "8.1. Polling for payment status..."
        $statusResult = Invoke-PollPaymentStatus -paymentId $paymentId -token $tenantToken -maxAttempts 6 -delaySeconds 5
        
        if ($statusResult.status -eq "pending") {
            Write-Host "Payment still pending after polling - simulating successful callback..."
            
            # Simulate successful deposit callback
            Write-Host "8.2. Simulating successful deposit callback for payment ID: $paymentId"
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
                
                # Check final status after callback
                Start-Sleep -Seconds 2
                $finalStatus = Invoke-GetAuth -url "$baseUrl/api/payments/deposit-status/$paymentId/" -token $tenantToken
                Write-Host "Final payment status after callback: $($finalStatus.status)"
                
                if ($finalStatus.status -eq "success") {
                    Write-Host "SUCCESS: Deposit payment completed and tenant assigned to unit"
                } else {
                    Write-Host "WARNING: Deposit payment status is $($finalStatus.status) after callback"
                }
            } catch {
                Write-Host "Deposit callback simulation failed: $($_.Exception.Message)"
            }
        } elseif ($statusResult.status -eq "success") {
            Write-Host "SUCCESS: Deposit payment already completed via callback"
        } else {
            Write-Host "Payment failed with status: $($statusResult.status)"
        }
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Deposit initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
}

# 8.3. Test failed payment scenario
Write-Host "8.3. Testing failed payment scenario..."
try {
    $failedDepositBody = @{
        unit_id = $unitId
    } | ConvertTo-Json
    
    $failedDepositResponse = Invoke-PostJson -url "$baseUrl/api/payments/initiate-deposit/" -headers $tenantHeaders -body $failedDepositBody
    
    if ($failedDepositResponse.payment_id) {
        $failedPaymentId = $failedDepositResponse.payment_id
        Write-Host "Created payment for failure test: $failedPaymentId"
        
        # Simulate failed callback
        Write-Host "Simulating failed deposit callback..."
        $failedCallbackBody = @"
{
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "test-failed-request",
            "CheckoutRequestID": "ws_CO_test_failed",
            "ResultCode": 1032,
            "ResultDesc": "Request Cancelled by user."
        }
    }
}
"@
        $failedCallbackResponse = Invoke-PostJson -url "$baseUrl/api/payments/callback/deposit/" -body $failedCallbackBody
        Write-Host "Failed callback response: $($failedCallbackResponse | ConvertTo-Json)"
        
        # Check status of failed payment
        Start-Sleep -Seconds 2
        $failedStatus = Invoke-GetAuth -url "$baseUrl/api/payments/deposit-status/$failedPaymentId/" -token $tenantToken
        Write-Host "Failed payment status: $($failedStatus.status)"
        
        if ($failedStatus.status -eq "failed") {
            Write-Host "SUCCESS: Failed payment properly handled - tenant not assigned"
        }
    }
} catch {
    Write-Host "Failed payment test error: $($_.Exception.Message)"
}

# 9. Verify tenant assignment by checking unit status
Write-Host "9. Verifying unit assignment status..."
try {
    $updatedUnitsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/properties/$propertyId/units/" -token $landlordToken
    $assignedUnit = $updatedUnitsResponse | Where-Object { $_.id -eq $unitId } | Select-Object -First 1
    
    if ($assignedUnit.tenant -eq $tenantId) {
        Write-Host "SUCCESS: Tenant $tenantId is properly assigned to unit $unitId"
    } else {
        Write-Host "UNIT STATUS: Unit $unitId tenant: $($assignedUnit.tenant), available: $($assignedUnit.is_available)"
    }
} catch {
    Write-Host "Error checking unit assignment: $($_.Exception.Message)"
}

# 10. Initiate Rent Payment as Tenant (100 KSH) - Only if deposit was successful
Write-Host "10. Initiating rent payment (100 KSH)..."
$rentBody = @{
    amount = "100"
} | ConvertTo-Json

$startTime = Get-Date
Write-Host "Rent initiation started at: $startTime"
try {
    $rentResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push/$unitId/" -headers $tenantHeaders -body $rentBody
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Rent STK push initiated in $($duration.TotalSeconds) seconds: $($rentResponse | ConvertTo-Json)"
    
    # Simulate successful rent callback
    if ($rentResponse.payment_id) {
        $rentPaymentId = $rentResponse.payment_id
        Write-Host "Simulating successful rent callback for payment ID: $rentPaymentId"
        $rentCallbackBody = @"
{
    "Body": {
        "stkCallback": {
            "ResultCode": 0,
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 100},
                    {"Name": "MpesaReceiptNumber", "Value": "RENT$rentPaymentId"},
                    {"Name": "AccountReference", "Value": "$rentPaymentId"},
                    {"Name": "PhoneNumber", "Value": "$tenantPhone"}
                ]
            }
        }
    }
}
"@
        $rentCallbackResponse = Invoke-PostJson -url "$baseUrl/api/payments/callback/rent/" -body $rentCallbackBody
        Write-Host "Rent callback simulated: $($rentCallbackResponse | ConvertTo-Json)"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Rent initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
}

# 10.1. Test rent-payments/ list
Write-Host "10.1. Listing rent payments..."
$rentPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-payments/" -token $tenantToken
Write-Host "Rent payments: $($rentPaymentsResponse | ConvertTo-Json)"

# 11. Create Report as Tenant
Write-Host "11. Creating report as tenant..."
$reportBody = @{
    unit = $unitId
    issue_title = "Test Report"
    issue_category = "maintenance"
    description = "This is a test report for maintenance."
    priority_level = "low"
} | ConvertTo-Json

try {
    $reportResponse = Invoke-PostJson -url "$baseUrl/api/communication/reports/create/" -headers $tenantHeaders -body $reportBody
    Write-Host "Report created. ID: $($reportResponse.id)"
    $reportId = $reportResponse.id
} catch {
    Write-Host "Report creation failed: $($_.Exception.Message)"
}

# 12. Initiate Subscription Payment as Landlord (50 KSH test plan)
Write-Host "12. Initiating subscription payment (50 KSH test plan)..."
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
    
    # Simulate successful subscription callback
    if ($subscriptionResponse.payment_id) {
        $subPaymentId = $subscriptionResponse.payment_id
        Write-Host "Simulating successful subscription callback for payment ID: $subPaymentId"
        $subCallbackBody = @"
{
    "Body": {
        "stkCallback": {
            "ResultCode": 0,
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 50},
                    {"Name": "MpesaReceiptNumber", "Value": "SUB$subPaymentId"},
                    {"Name": "AccountReference", "Value": "$subPaymentId"},
                    {"Name": "PhoneNumber", "Value": "$landlordPhone"}
                ]
            }
        }
    }
}
"@
        $subCallbackResponse = Invoke-PostJson -url "$baseUrl/api/payments/callback/subscription/" -body $subCallbackBody
        Write-Host "Subscription callback simulated: $($subCallbackResponse | ConvertTo-Json)"
    }
} catch {
    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Subscription initiation failed in $($duration.TotalSeconds) seconds: $($_.Exception.Message)"
}

# 12.1. Test subscription-payments/ list
Write-Host "12.1. Listing subscription payments..."
try {
    $subscriptionPaymentsResponse = Invoke-GetAuth -url "$baseUrl/api/payments/subscription-payments/" -token $landlordToken
    Write-Host "Subscription payments: $($subscriptionPaymentsResponse | ConvertTo-Json)"
} catch {
    Write-Host "Subscription payments list failed: $($_.Exception.Message)"
}

# 13. Test rent summary for landlord
Write-Host "13. Testing rent summary..."
try {
    $rentSummaryResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-summary/" -token $landlordToken
    Write-Host "Rent summary: $($rentSummaryResponse | ConvertTo-Json)"
} catch {
    Write-Host "Rent summary failed: $($_.Exception.Message)"
}

# ------------------------------
# TEST CLEANUP AND SIMULATION ENDPOINTS
# ------------------------------
Write-Host "14. Testing cleanup pending payments endpoint..."
try {
    $cleanupResponse = Invoke-PostAuth -url "$baseUrl/api/payments/cleanup-pending-payments/" -token $landlordToken -body "{}"
    Write-Host "Cleanup response: $($cleanupResponse | ConvertTo-Json)"
} catch {
    Write-Host "Cleanup test failed: $($_.Exception.Message)"
}

Write-Host "15. Testing simulate deposit callback endpoint..."
try {
    # First create a pending deposit payment to simulate
    $simulateDepositBody = @{
        unit_id = $unitId
    } | ConvertTo-Json

    $simulateDepositResponse = Invoke-PostJson -url "$baseUrl/api/payments/initiate-deposit/" -headers $tenantHeaders -body $simulateDepositBody
    if ($simulateDepositResponse.payment_id) {
        $simulatePaymentId = $simulateDepositResponse.payment_id
        Write-Host "Created payment for simulation: $simulatePaymentId"

        # Now simulate the callback
        $simulateCallbackResponse = Invoke-PostAuth -url "$baseUrl/api/payments/simulate-deposit-callback/?payment_id=$simulatePaymentId" -token $tenantToken -body "{}"
        Write-Host "Simulate callback response: $($simulateCallbackResponse | ConvertTo-Json)"
    }
} catch {
    Write-Host "Simulate callback test failed: $($_.Exception.Message)"
}

Write-Host "All tests completed with new payment flow and cleanup/simulation features!"
Write-Host "Key improvements:"
Write-Host "- Deposit payments now wait for callback confirmation"
Write-Host "- Tenant assignment happens ONLY after successful payment"
Write-Host "- Payment status polling replaces immediate success assumption"
Write-Host "- Proper handling of both success and failure scenarios"
Write-Host "- Added cleanup endpoint for pending payments older than 10 minutes"
Write-Host "- Added simulation endpoint for testing deposit callbacks"
