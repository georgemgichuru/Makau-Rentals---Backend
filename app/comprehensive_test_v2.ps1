# ============================================================
# Makau Rentals - Real M-Pesa STK Push Test (ASCII Safe)
# ============================================================

$baseUrl = "https://makau-rentals-backend.onrender.com"

function Invoke-PostJson {
    param([string]$url, [hashtable]$headers = @{}, [string]$body)
    try {
        return Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -ContentType "application/json"
    } catch {
        Write-Host "POST error: $url"
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host ($reader.ReadToEnd())
        }
        throw
    }
}

function Invoke-GetAuth {
    param([string]$url, [string]$token)
    $headers = @{ Authorization = "Bearer $token" }
    return Invoke-RestMethod -Uri $url -Method GET -Headers $headers
}

function Invoke-PollPaymentStatus {
    param(
        [string]$paymentId,
        [string]$token,
        [int]$attempts = 30,
        [int]$delay = 10
    )
    for ($i = 1; $i -le $attempts; $i++) {
        Write-Host "Polling payment status ($i/$attempts)..."
        Start-Sleep -Seconds $delay
        try {
            $resp = Invoke-GetAuth "$baseUrl/api/payments/deposit-status/$paymentId/" -token $token
            if ($resp.status -ne "Pending") { return $resp }
        } catch {
            Write-Host "Error checking status: $($_.Exception.Message)"
        }
    }
    return @{ status = "timeout" }
}

# ------------------ SETUP ------------------

$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$landlordEmail = "real_landlord_$timestamp@example.com"
$tenantEmail   = "real_tenant_$timestamp@example.com"
$password      = "testpass123"
$phone         = "254722714334"    # Replace with your actual Safaricom line

# ------------------ LANDLORD ------------------

Write-Host "Signing up landlord..."
$landlordBody = @{
    email = $landlordEmail
    full_name = "Real Landlord"
    user_type = "landlord"
    password = $password
    phone_number = $phone
} | ConvertTo-Json
$landlord = Invoke-PostJson "$baseUrl/api/accounts/signup/" -body $landlordBody
$loginBody = @{ email=$landlordEmail; password=$password; user_type="landlord" } | ConvertTo-Json
$landlordToken = (Invoke-PostJson "$baseUrl/api/accounts/token/" -body $loginBody).access
$headers = @{ Authorization = "Bearer $landlordToken" }
$landlordCode = $landlord.landlord_code

Write-Host "Creating property..."
$prop = Invoke-PostJson "$baseUrl/api/accounts/properties/create/" -headers $headers -body (@{name="Real Property";city="Nairobi";state="Kenya";unit_count=1} | ConvertTo-Json)
$propId = $prop.id

Write-Host "Creating unit type..."
$unitType = Invoke-PostJson "$baseUrl/api/accounts/unit-types/" -headers $headers -body (@{name="Test 1BR";deposit=10;rent=100;unit_count=1;property_id=$propId} | ConvertTo-Json)
$unitTypeId = $unitType.id
$units = Invoke-GetAuth "$baseUrl/api/accounts/properties/$propId/units/" -token $landlordToken
$unitId = $units[0].id
Write-Host "Property=$propId Unit=$unitId"

# ------------------ TENANT ------------------

Write-Host "Creating tenant..."
$tenantBody = @{
    email=$tenantEmail
    full_name="Real Tenant"
    user_type="tenant"
    password=$password
    phone_number=$phone
    landlord_code=$landlordCode
} | ConvertTo-Json
Invoke-PostJson "$baseUrl/api/accounts/signup/" -body $tenantBody
$tenantLogin = @{email=$tenantEmail;password=$password;user_type="tenant"} | ConvertTo-Json
$tenantToken = (Invoke-PostJson "$baseUrl/api/accounts/token/" -body $tenantLogin).access
$tenantHeaders = @{ Authorization = "Bearer $tenantToken" }

# ------------------ REAL DEPOSIT TEST ------------------

Write-Host ""
Write-Host "Initiating REAL deposit STK Push (10 KSH)..."
$depositResp = Invoke-PostJson "$baseUrl/api/payments/initiate-deposit/" -headers $tenantHeaders -body (@{unit_id=$unitId} | ConvertTo-Json)

if (-not $depositResp.payment_id) {
    Write-Host "Error: Deposit initiation did not return payment_id."
    exit
}

$paymentId = $depositResp.payment_id
Write-Host "STK Push sent. Payment ID = $paymentId"
Write-Host "Check your phone and approve the M-Pesa request."

# Wait for real callback
$status = Invoke-PollPaymentStatus -paymentId $paymentId -token $tenantToken

if ($status.status -eq "success") {
    Write-Host "Deposit confirmed via REAL M-Pesa callback!"
} elseif ($status.status -eq "Pending" -or $status.status -eq "timeout") {
    Write-Host "Payment still pending. You might not have accepted the STK push yet."
    Write-Host "You can re-check manually with:"
    Write-Host "Invoke-GetAuth \"$baseUrl/api/payments/deposit-status/$paymentId/\" -token <tenantToken>"
} else {
    Write-Host "Payment failed. Status: $($status.status)"
}

Write-Host ""
Write-Host "Test completed."
# ============================================================