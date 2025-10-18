# Comprehensive test script v5 for Makau Rentals backend flows - IMPROVED VERSION
# UPDATED to match actual API endpoints and JSON structure from your codebase
# Modularized, with validation, error handling, cleanup, and configurable parameters

param (
    [decimal]$DepositAmount = 10.00,
    [decimal]$RentAmount = 100.00,
    [decimal]$SubscriptionAmount = 50.00,
    [switch]$SkipCleanup,
    [switch]$Verbose
)

# Hardcoded API base URL
$BaseUrl = "https://makau-rentals-backend.onrender.com"

# Global variables for test results
$global:TestResults = @()
$global:TestData = @{}

# Function to log test results
function Log-TestResult {
    param (
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = ""
    )
    $result = @{
        TestName = $TestName
        Passed = $Passed
        Message = $Message
        Timestamp = Get-Date
    }
    $global:TestResults += $result
    if ($Passed) {
        Write-Host "✓ $TestName" -ForegroundColor Green
    } else {
        Write-Host "✗ $TestName" -ForegroundColor Red
        if ($Message) { Write-Host "  $Message" -ForegroundColor Red }
    }
}

# Function to validate response
function Validate-Response {
    param (
        [object]$Response,
        [string[]]$RequiredFields = @(),
        [int]$ExpectedStatus = 200
    )
    if (-not $Response) {
        return $false
    }
    foreach ($field in $RequiredFields) {
        if (-not $Response.PSObject.Properties.Match($field)) {
            return $false
        }
    }
    return $true
}

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
        Write-Host ("Error in POST to " + $url + ": " + $($_.Exception.Message))
        if ($_.Exception.Response) {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $responseBody = $reader.ReadToEnd()
            Write-Host ("Response body: " + $responseBody)
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
        Write-Host ("Error in GET to " + $url + ": " + $($_.Exception.Message))
        throw
    }
}

# Function to simulate deposit callback and check status
function Invoke-SimulateDepositCallback {
    param (
        [string]$paymentId,
        [string]$token
    )

    Write-Host "Simulating deposit callback for payment ID: $paymentId..."
    $simulateBody = @{
        payment_id = $paymentId
    } | ConvertTo-Json

    try {
        $simulateResponse = Invoke-PostJson -url "$BaseUrl/api/payments/simulate-deposit-callback/" -headers @{ Authorization = "Bearer $token" } -body $simulateBody
        Write-Host "Deposit callback simulated successfully."

        # Now check the final status
        $statusResponse = Invoke-GetAuth -url "$BaseUrl/api/payments/deposit-status/$paymentId/" -token $token
        Write-Host "Final deposit payment status: $($statusResponse.status)"
        return $statusResponse
    } catch {
        Write-Host "Error simulating deposit callback: $($_.Exception.Message)"
        return @{ status = "error"; message = $_.Exception.Message }
    }
}

# Test functions
function Test-LandlordSignup {
    try {
        $body = @{
            email = $global:TestData.LandlordEmail
            full_name = $global:TestData.LandlordFullName
            user_type = "landlord"
            password = $global:TestData.LandlordPassword
            phone_number = $global:TestData.LandlordPhone
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/signup/" -body $body
        if (Validate-Response -Response $response -RequiredFields @("id", "landlord_code")) {
            $global:TestData.LandlordId = $response.id
            $global:TestData.LandlordCode = $response.landlord_code
            Log-TestResult -TestName "Landlord Signup" -Passed $true
        } else {
            Log-TestResult -TestName "Landlord Signup" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Landlord Signup" -Passed $false -Message $_.Exception.Message
    }
}

function Test-LandlordLogin {
    try {
        $body = @{
            email = $global:TestData.LandlordEmail
            password = $global:TestData.LandlordPassword
            user_type = "landlord"
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/token/" -body $body
        if (Validate-Response -Response $response -RequiredFields @("access")) {
            $global:TestData.LandlordToken = $response.access
            Log-TestResult -TestName "Landlord Login" -Passed $true
        } else {
            Log-TestResult -TestName "Landlord Login" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Landlord Login" -Passed $false -Message $_.Exception.Message
    }
}

function Test-PropertyCreation {
    try {
        $body = @{
            name = "Test Property $timestamp"
            city = "Nairobi"
            state = "Kenya"
            unit_count = 2
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/properties/create/" -headers @{ Authorization = "Bearer $($global:TestData.LandlordToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("id")) {
            $global:TestData.PropertyId = $response.id
            Log-TestResult -TestName "Property Creation" -Passed $true
        } else {
            Log-TestResult -TestName "Property Creation" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Property Creation" -Passed $false -Message $_.Exception.Message
    }
}

function Test-UnitTypeCreation {
    try {
        $body = @{
            name = "Studio Minimal $timestamp"
            deposit = $DepositAmount
            rent = $RentAmount
            number_of_units = 1
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/unit-types/" -headers @{ Authorization = "Bearer $($global:TestData.LandlordToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("id")) {
            $global:TestData.UnitTypeId = $response.id
            Log-TestResult -TestName "Unit Type Creation" -Passed $true
        } else {
            Log-TestResult -TestName "Unit Type Creation" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Unit Type Creation" -Passed $false -Message $_.Exception.Message
    }
}

function Test-UnitCreation {
    try {
        $body = @{
            property_obj = $global:TestData.PropertyId
            unit_type = $global:TestData.UnitTypeId
            unit_number = "101"
            bedrooms = 1
            bathrooms = 1
            rent = $RentAmount
            deposit = $DepositAmount
            is_available = $true
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/units/create/" -headers @{ Authorization = "Bearer $($global:TestData.LandlordToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("id", "unit_code")) {
            $global:TestData.UnitId = $response.id
            $global:TestData.UnitCode = $response.unit_code
            Log-TestResult -TestName "Unit Creation" -Passed $true
        } else {
            Log-TestResult -TestName "Unit Creation" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Unit Creation" -Passed $false -Message $_.Exception.Message
    }
}

function Test-TenantSignup {
    try {
        $body = @{
            email = $global:TestData.TenantEmail
            full_name = $global:TestData.TenantFullName
            user_type = "tenant"
            password = $global:TestData.TenantPassword
            phone_number = $global:TestData.TenantPhone
            landlord_code = $global:TestData.LandlordCode
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/signup/" -body $body
        if (Validate-Response -Response $response -RequiredFields @("id")) {
            $global:TestData.TenantId = $response.id
            Log-TestResult -TestName "Tenant Signup" -Passed $true
        } else {
            Log-TestResult -TestName "Tenant Signup" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Tenant Signup" -Passed $false -Message $_.Exception.Message
    }
}

function Test-TenantLogin {
    try {
        $body = @{
            email = $global:TestData.TenantEmail
            password = $global:TestData.TenantPassword
            user_type = "tenant"
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/accounts/token/" -body $body
        if (Validate-Response -Response $response -RequiredFields @("access")) {
            $global:TestData.TenantToken = $response.access
            Log-TestResult -TestName "Tenant Login" -Passed $true
        } else {
            Log-TestResult -TestName "Tenant Login" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Tenant Login" -Passed $false -Message $_.Exception.Message
    }
}

function Test-DepositPayment {
    try {
        $body = @{
            unit_id = $global:TestData.UnitId
            test = $true
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/payments/initiate-deposit/" -headers @{ Authorization = "Bearer $($global:TestData.TenantToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("payment_id")) {
            $global:TestData.PaymentId = $response.payment_id
            # Simulate callback
            $statusResult = Invoke-SimulateDepositCallback -paymentId $response.payment_id -token $global:TestData.TenantToken
            if ($statusResult.status -eq "Success") {
                Log-TestResult -TestName "Deposit Payment" -Passed $true
            } else {
                Log-TestResult -TestName "Deposit Payment" -Passed $false -Message "Payment status: $($statusResult.status)"
            }
        } else {
            Log-TestResult -TestName "Deposit Payment" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Deposit Payment" -Passed $false -Message $_.Exception.Message
    }
}

function Test-RentPayment {
    try {
        $body = @{
            amount = $RentAmount.ToString()
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/payments/stk-push/$($global:TestData.UnitId)/" -headers @{ Authorization = "Bearer $($global:TestData.TenantToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("checkout_request_id")) {
            Log-TestResult -TestName "Rent Payment" -Passed $true
        } else {
            Log-TestResult -TestName "Rent Payment" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Rent Payment" -Passed $false -Message $_.Exception.Message
    }
}

function Test-SubscriptionPayment {
    try {
        $body = @{
            plan = "starter"
            phone_number = $global:TestData.LandlordPhone
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/payments/stk-push-subscription/" -headers @{ Authorization = "Bearer $($global:TestData.LandlordToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("checkout_request_id")) {
            Log-TestResult -TestName "Subscription Payment" -Passed $true
        } else {
            Log-TestResult -TestName "Subscription Payment" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Subscription Payment" -Passed $false -Message $_.Exception.Message
    }
}

function Test-ReportCreation {
    try {
        $body = @{
            unit = $global:TestData.UnitId
            issue_title = "Test Maintenance Report $timestamp"
            issue_category = "maintenance"
            description = "This is a test report for maintenance issues."
            priority_level = "medium"
        } | ConvertTo-Json

        $response = Invoke-PostJson -url "$BaseUrl/api/communication/reports/create/" -headers @{ Authorization = "Bearer $($global:TestData.TenantToken)" } -body $body
        if (Validate-Response -Response $response -RequiredFields @("id")) {
            $global:TestData.ReportId = $response.id
            Log-TestResult -TestName "Report Creation" -Passed $true
        } else {
            Log-TestResult -TestName "Report Creation" -Passed $false -Message "Invalid response structure"
        }
    } catch {
        Log-TestResult -TestName "Report Creation" -Passed $false -Message $_.Exception.Message
    }
}

function Test-StatsAndSummaries {
    # Test various stats endpoints
    $tests = @(
        @{ Name = "Rent Payments List"; Url = "$BaseUrl/api/payments/rent-payments/"; Token = $global:TestData.TenantToken },
        @{ Name = "Subscription Payments List"; Url = "$BaseUrl/api/payments/subscription-payments/"; Token = $global:TestData.LandlordToken },
        @{ Name = "Rent Summary"; Url = "$BaseUrl/api/payments/rent-summary/"; Token = $global:TestData.LandlordToken },
        @{ Name = "Dashboard Stats"; Url = "$BaseUrl/api/accounts/dashboard-stats/"; Token = $global:TestData.LandlordToken },
        @{ Name = "Subscription Status"; Url = "$BaseUrl/api/accounts/subscription-status/"; Token = $global:TestData.LandlordToken }
    )

    foreach ($test in $tests) {
        try {
            $response = Invoke-GetAuth -url $test.Url -token $test.Token
            Log-TestResult -TestName $test.Name -Passed $true
        } catch {
            Log-TestResult -TestName $test.Name -Passed $false -Message $_.Exception.Message
        }
    }
}

function Test-Cleanup {
    if ($SkipCleanup) {
        Write-Host "Skipping cleanup as requested."
        return
    }

    Write-Host "Cleaning up test data..."
    # Note: Actual cleanup would require DELETE endpoints, which may not exist
    # For now, just log that cleanup was attempted
    Log-TestResult -TestName "Cleanup" -Passed $true -Message "Cleanup attempted (DELETE endpoints not implemented)"
}

function Show-TestSummary {
    $passed = ($global:TestResults | Where-Object { $_.Passed }).Count
    $total = $global:TestResults.Count
    $failed = $total - $passed

    Write-Host "`n=== TEST SUMMARY ===" -ForegroundColor Cyan
    Write-Host "Total Tests: $total" -ForegroundColor White
    Write-Host "Passed: $passed" -ForegroundColor Green
    Write-Host "Failed: $failed" -ForegroundColor Red

    if ($failed -gt 0) {
        Write-Host "`nFailed Tests:" -ForegroundColor Red
        $global:TestResults | Where-Object { -not $_.Passed } | ForEach-Object {
            Write-Host "- $($_.TestName): $($_.Message)" -ForegroundColor Red
        }
    }

    Write-Host "`nNote: Complete the M-Pesa payments on your phone to test the full callback flow!" -ForegroundColor Yellow
}

# Main execution
try {
    # Initialize test data
    $timestamp = Get-Date -Format 'yyyyMMddHHmmss'
    $global:TestData = @{
        LandlordEmail = "test_landlord_$timestamp@example.com"
        LandlordPassword = "testpass123"
        LandlordFullName = "Test Landlord"
        LandlordPhone = "254708374149"
        TenantEmail = "test_tenant_$timestamp@example.com"
        TenantPassword = "testpass123"
        TenantFullName = "Test Tenant"
        TenantPhone = "254708374149"
    }

    Write-Host "Starting Makau Rentals API Tests..." -ForegroundColor Cyan
    Write-Host "Timestamp: $timestamp" -ForegroundColor Gray
    Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray

    # Run tests in sequence
    Test-LandlordSignup
    Test-LandlordLogin
    Test-PropertyCreation
    Test-UnitTypeCreation
    Test-UnitCreation
    Test-TenantSignup
    Test-TenantLogin
    Test-DepositPayment
    Test-RentPayment
    Test-SubscriptionPayment
    Test-ReportCreation
    Test-StatsAndSummaries
    Test-Cleanup

    # Show final summary
    Show-TestSummary

} catch {
    Write-Host "Unhandled error in main execution: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
}
