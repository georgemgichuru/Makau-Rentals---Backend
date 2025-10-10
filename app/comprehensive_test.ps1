# Comprehensive test script for Makau Rentals backend flows
# Tests: Tenant and Landlord signup, login, subscription payment, rent payment, report system

$baseUrl = "http://localhost"

# Function to perform POST request with JSON body
function Invoke-PostJson {
    param (
        [string]$url,
        [hashtable]$headers = @{},
        [string]$body
    )
    Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -ContentType "application/json"
}

# Function to perform GET request with Authorization header
function Invoke-GetAuth {
    param (
        [string]$url,
        [string]$token
    )
    $headers = @{ Authorization = "Bearer $token" }
    Invoke-RestMethod -Uri $url -Method GET -Headers $headers
}

# Function to perform PATCH request with Authorization header
function Invoke-PatchAuth {
    param (
        [string]$url,
        [string]$token,
        [string]$body
    )
    $headers = @{ Authorization = "Bearer $token" }
    Invoke-RestMethod -Uri $url -Method PATCH -Headers $headers -Body $body -ContentType "application/json"
}

# Test data
$landlordEmail = "test_landlord@example.com"
$landlordPassword = "testpass123"
$landlordFullName = "Test Landlord"
$landlordPhone = "254712345678"

$tenantEmail = "test_tenant@example.com"
$tenantPassword = "testpass123"
$tenantFullName = "Test Tenant"
$tenantPhone = "254798765432"

# 1. Signup Landlord with property and unit
Write-Host "1. Signing up landlord..."
$landlordSignupBody = @{
    email = $landlordEmail
    full_name = $landlordFullName
    user_type = "landlord"
    password = $landlordPassword
    phone_number = $landlordPhone
    properties = @(
        @{
            name = "Test Property"
            city = "Nairobi"
            state = "Kenya"
            unit_count = 1
            vacant_units = 1
            unit_type = "1 Bedroom"
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $landlordSignupResponse = Invoke-PostJson -url "$baseUrl/api/accounts/users/" -body $landlordSignupBody
    Write-Host "Landlord signup successful:" ($landlordSignupResponse | ConvertTo-Json)
    $landlordCode = $landlordSignupResponse.landlord_code
    Write-Host "Landlord code: $landlordCode"
} catch {
    Write-Host "Landlord signup failed:" $_.Exception.Message
    exit 1
}

# 2. Login Landlord
Write-Host "2. Logging in landlord..."
$landlordLoginBody = @{
    email = $landlordEmail
    password = $landlordPassword
    user_type = "landlord"
} | ConvertTo-Json

try {
    $landlordLoginResponse = Invoke-PostJson -url "$baseUrl/api/accounts/token/" -body $landlordLoginBody
    Write-Host "Landlord login successful:" ($landlordLoginResponse | ConvertTo-Json)
    $landlordToken = $landlordLoginResponse.access
} catch {
    Write-Host "Landlord login failed:" $_.Exception.Message
    exit 1
}

# 3. Initiate Subscription Payment (Starter plan)
Write-Host "3. Initiating subscription payment..."
$subscriptionBody = @{
    plan = "starter"
    phone_number = $landlordPhone
} | ConvertTo-Json

try {
    $subscriptionResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push-subscription/" -body $subscriptionBody
    Write-Host "Subscription STK push initiated:" ($subscriptionResponse | ConvertTo-Json)
} catch {
    Write-Host "Subscription payment initiation failed:" $_.Exception.Message
}

# 4. Signup Tenant
Write-Host "4. Signing up tenant..."
$tenantSignupBody = @{
    email = $tenantEmail
    full_name = $tenantFullName
    user_type = "tenant"
    password = $tenantPassword
    phone_number = $tenantPhone
    landlord_code = $landlordCode
    unit_code = "U-1-1"  # Assuming property id=1, unit=1
} | ConvertTo-Json

try {
    $tenantSignupResponse = Invoke-PostJson -url "$baseUrl/api/accounts/users/" -body $tenantSignupBody
    Write-Host "Tenant signup successful:" ($tenantSignupResponse | ConvertTo-Json)
    $tenantId = $tenantSignupResponse.id
} catch {
    Write-Host "Tenant signup failed:" $_.Exception.Message
    exit 1
}

# 5. Login Tenant
Write-Host "5. Logging in tenant..."
$tenantLoginBody = @{
    email = $tenantEmail
    password = $tenantPassword
    user_type = "tenant"
} | ConvertTo-Json

try {
    $tenantLoginResponse = Invoke-PostJson -url "$baseUrl/api/accounts/token/" -body $tenantLoginBody
    Write-Host "Tenant login successful:" ($tenantLoginResponse | ConvertTo-Json)
    $tenantToken = $tenantLoginResponse.access
} catch {
    Write-Host "Tenant login failed:" $_.Exception.Message
    exit 1
}

# 6. Get unit types for tenant (to get unit_type_id for deposit)
Write-Host "6. Getting unit types..."
try {
    $unitTypesResponse = Invoke-GetAuth -url "$baseUrl/api/payments/unit-types/?landlord_code=$landlordCode" -token $tenantToken
    Write-Host "Unit types:" ($unitTypesResponse | ConvertTo-Json)
    $unitTypeId = $unitTypesResponse[0].id
    Write-Host "Unit type ID: $unitTypeId"
} catch {
    Write-Host "Failed to get unit types:" $_.Exception.Message
}

# 7. Initiate Deposit Payment
Write-Host "7. Initiating deposit payment..."
$depositBody = @{
    phone_number = $tenantPhone
    unit_type_id = $unitTypeId
    tenant_email = $tenantEmail
} | ConvertTo-Json

try {
    $depositResponse = Invoke-PostJson -url "$baseUrl/api/payments/initiate-deposit/" -body $depositBody
    Write-Host "Deposit STK push initiated:" ($depositResponse | ConvertTo-Json)
} catch {
    Write-Host "Deposit payment initiation failed:" $_.Exception.Message
}

# 8. Assign unit to tenant (as landlord, after deposit - but since no callback, manually assign for testing)
# First, get unit ID
Write-Host "8. Getting landlord properties..."
try {
    $propertiesResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/properties/" -token $landlordToken
    Write-Host "Properties:" ($propertiesResponse | ConvertTo-Json)
    $propertyId = $propertiesResponse[0].id
    Write-Host "Property ID: $propertyId"
} catch {
    Write-Host "Failed to get properties:" $_.Exception.Message
}

# Get units
Write-Host "Getting units..."
try {
    $unitsResponse = Invoke-GetAuth -url "$baseUrl/api/accounts/properties/$propertyId/units/" -token $landlordToken
    Write-Host "Units:" ($unitsResponse | ConvertTo-Json)
    $unitId = $unitsResponse[0].id
    Write-Host "Unit ID: $unitId"
} catch {
    Write-Host "Failed to get units:" $_.Exception.Message
}

# Assign tenant to unit (assuming deposit paid for testing)
Write-Host "Assigning tenant to unit..."
try {
    $assignResponse = Invoke-PostJson -url "$baseUrl/api/accounts/assign-tenant/$unitId/$tenantId/" -headers @{ Authorization = "Bearer $landlordToken" } -body "{}"
    Write-Host "Tenant assigned to unit:" ($assignResponse | ConvertTo-Json)
} catch {
    Write-Host "Failed to assign tenant:" $_.Exception.Message
}

# 9. Initiate Rent Payment
Write-Host "9. Initiating rent payment..."
$rentBody = @{
    amount = "2000"  # Assuming rent is 2000
} | ConvertTo-Json

try {
    $rentResponse = Invoke-PostJson -url "$baseUrl/api/payments/stk-push/$unitId/" -headers @{ Authorization = "Bearer $tenantToken" } -body $rentBody
    Write-Host "Rent STK push initiated:" ($rentResponse | ConvertTo-Json)
} catch {
    Write-Host "Rent payment initiation failed:" $_.Exception.Message
}

# 10. Create a report as tenant
Write-Host "10. Creating a report as tenant..."
$reportBody = @{
    unit = $unitId
    title = "Test Report"
    description = "This is a test report"
    priority_level = "normal"
} | ConvertTo-Json

try {
    $reportResponse = Invoke-PostJson -url "$baseUrl/api/communication/reports/" -headers @{ Authorization = "Bearer $tenantToken" } -body $reportBody
    Write-Host "Report created:" ($reportResponse | ConvertTo-Json)
} catch {
    Write-Host "Failed to create report:" $_.Exception.Message
}

# 11. View open reports as landlord
Write-Host "11. Viewing open reports as landlord..."
try {
    $reportsResponse = Invoke-GetAuth -url "$baseUrl/api/communication/reports/open/" -token $landlordToken
    Write-Host "Open reports:" ($reportsResponse | ConvertTo-Json)
} catch {
    Write-Host "Failed to get reports:" $_.Exception.Message
}

# 12. Get rent summary as landlord
Write-Host "12. Getting rent summary as landlord..."
try {
    $summaryResponse = Invoke-GetAuth -url "$baseUrl/api/payments/rent-summary/" -token $landlordToken
    Write-Host "Rent summary:" ($summaryResponse | ConvertTo-Json)
} catch {
    Write-Host "Failed to get rent summary:" $_.Exception.Message
}

Write-Host "Testing completed."
