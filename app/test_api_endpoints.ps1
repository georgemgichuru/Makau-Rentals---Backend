# PowerShell script to test API endpoints with correct headers and JSON body

# Function to perform POST request with JSON body
function Invoke-PostJson {
    param (
        [string]$url,
        [hashtable]$headers,
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

# Test login with tenant user_type
$loginUrl = "http://localhost/api/accounts/token/"
$loginBodyTenant = '{"email":"test@example.com","password":"testpass123","user_type":"tenant"}'
$headers = @{}

Write-Host "Testing login for tenant..."
try {
    $loginResponseTenant = Invoke-PostJson -url $loginUrl -headers $headers -body $loginBodyTenant
    Write-Host "Access Token:" $loginResponseTenant.access
    Write-Host "Refresh Token:" $loginResponseTenant.refresh
} catch {
    Write-Host "Login failed for tenant:" $_.Exception.Message
}

# Test login with landlord user_type
$loginBodyLandlord = '{"email":"landlord@example.com","password":"landlord123","user_type":"landlord"}'
Write-Host "Testing login for landlord..."
try {
    $loginResponseLandlord = Invoke-PostJson -url $loginUrl -headers $headers -body $loginBodyLandlord
    Write-Host "Access Token:" $loginResponseLandlord.access
    Write-Host "Refresh Token:" $loginResponseLandlord.refresh
} catch {
    Write-Host "Login failed for landlord:" $_.Exception.Message
}

# Test get unit-types with tenant token if login succeeded
if ($loginResponseTenant -and $loginResponseTenant.access) {
    $unitTypesUrl = "http://localhost/api/payments/unit-types/"
    Write-Host "Testing get unit-types with tenant token..."
    try {
        $unitTypesResponse = Invoke-GetAuth -url $unitTypesUrl -token $loginResponseTenant.access
        Write-Host "Unit Types:" ($unitTypesResponse | ConvertTo-Json)
    } catch {
        Write-Host "Failed to get unit types:" $_.Exception.Message
    }

    # Test token refresh
    $refreshUrl = "http://localhost/api/accounts/token/refresh/"
    $refreshBody = "{`"refresh`":`"$($loginResponseTenant.refresh)`"}"
    Write-Host "Testing token refresh..."
    try {
        $refreshResponse = Invoke-PostJson -url $refreshUrl -headers $headers -body $refreshBody
        Write-Host "New Access Token:" $refreshResponse.access
    } catch {
        Write-Host "Token refresh failed:" $_.Exception.Message
    }
} else {
    Write-Host "Skipping unit-types and token refresh tests due to failed tenant login."
}

# Test login failure with wrong credentials
$loginBodyWrong = '{"email":"wrong@example.com","password":"wrongpass","user_type":"tenant"}'
Write-Host "Testing login failure with wrong credentials..."
try {
    $loginFailResponse = Invoke-PostJson -url $loginUrl -headers $headers -body $loginBodyWrong
} catch {
    Write-Host "Expected failure:" $_.Exception.Message
}
