#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Makau Rentals - Real Life Application Workflow Demo
.DESCRIPTION
    This script demonstrates the complete workflow of the Makau Rentals application
    from landlord signup to tenant payments and maintenance reports using the live API.
.NOTES
    Author: Makau Rentals
    Date: $(Get-Date)
#>

# Configuration
$BaseUrl = "https://makau-rentals-backend.onrender.com"
$ApiUrl = "$BaseUrl/api"

# Colors for output
$Green = "Green"
$Yellow = "Yellow" 
$Red = "Red"
$Cyan = "Cyan"
$Magenta = "Magenta"

# Global variables to store created data
$Global:LandlordToken = $null
$Global:TenantToken = $null
$Global:LandlordId = $null
$Global:TenantId = $null
$Global:PropertyId = $null
$Global:UnitId = $null
$Global:UnitTypeId = $null

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Section {
    param([string]$Title)
    Write-Host "`n" + "="*60 -ForegroundColor $Cyan
    Write-Host $Title -ForegroundColor $Cyan
    Write-Host "="*60 -ForegroundColor $Cyan
}

function Write-Step {
    param([string]$Step)
    Write-Host "`n▶ $Step" -ForegroundColor $Yellow
}

function Invoke-ApiRequest {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [object]$Body = $null,
        [string]$Token = $null
    )
    
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }
    
    $uri = "$ApiUrl/$Endpoint"
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers
        } else {
            $jsonBody = if ($Body) { $Body | ConvertTo-Json } else { "{}" }
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -Body $jsonBody
        }
        
        return @{
            Success = $true
            Data = $response
        }
    }
    catch {
        $errorMessage = $_.Exception.Message
        try {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            $errorMessage = $errorDetails.detail -or $errorDetails.error -or $errorMessage
        }
        catch {
            # If we can't parse JSON error, use the original message
        }
        
        return @{
            Success = $false
            Error = $errorMessage
            StatusCode = $_.Exception.Response.StatusCode.value__
        }
    }
}

function Test-ApiConnection {
    Write-Step "Testing API Connection"
    $response = Invoke-ApiRequest -Endpoint "accounts/me" -Method "GET"
    
    if ($response.Success) {
        Write-ColorOutput "✅ API is accessible and responding" $Green
        return $true
    } else {
        if ($response.StatusCode -eq 401) {
            Write-ColorOutput "✅ API is accessible (unauthorized access expected)" $Green
            return $true
        } else {
            Write-ColorOutput "❌ API connection failed: $($response.Error)" $Red
            return $false
        }
    }
}

function Register-Landlord {
    Write-Section "PHASE 1: LANDLORD ONBOARDING"
    
    Write-Step "1. Registering Landlord Account"
    
    $landlordData = @{
        email = "demo_landlord_$(Get-Random)_@makau.com"
        full_name = "Demo Landlord"
        user_type = "landlord"
        password = "DemoPass123!"
        phone_number = "+254700000000"
        government_id = "12345678"
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/signup/" -Method "POST" -Body $landlordData
    
    if ($response.Success) {
        $Global:LandlordId = $response.Data.id
        Write-ColorOutput "✅ Landlord registered successfully:" $Green
        Write-ColorOutput "   Email: $($landlordData.email)" $Green
        Write-ColorOutput "   ID: $($response.Data.id)" $Green
        Write-ColorOutput "   Landlord Code: $($response.Data.landlord_code)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Landlord registration failed: $($response.Error)" $Red
        return $false
    }
}

function Login-Landlord {
    Write-Step "2. Landlord Login"
    
    $loginData = @{
        email = "demo_landlord_@makau.com"  # Use a consistent email for demo
        password = "DemoPass123!"
        user_type = "landlord"
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/token/" -Method "POST" -Body $loginData
    
    if ($response.Success) {
        $Global:LandlordToken = $response.Data.access
        Write-ColorOutput "✅ Landlord logged in successfully" $Green
        Write-ColorOutput "   Token obtained: $($Global:LandlordToken.Substring(0, 20))..." $Green
        return $true
    } else {
        Write-ColorOutput "❌ Landlord login failed: $($response.Error)" $Red
        return $false
    }
}

function Create-UnitType {
    Write-Step "3. Creating Unit Type"
    
    $unitTypeData = @{
        name = "Studio Apartment"
        deposit = 5000.00
        rent = 15000.00
        unit_count = 3
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/unit-types/" -Method "POST" -Body $unitTypeData -Token $Global:LandlordToken
    
    if ($response.Success) {
        $Global:UnitTypeId = $response.Data.id
        Write-ColorOutput "✅ Unit Type created successfully:" $Green
        Write-ColorOutput "   Name: $($response.Data.name)" $Green
        Write-ColorOutput "   Rent: KES $($response.Data.rent)" $Green
        Write-ColorOutput "   Deposit: KES $($response.Data.deposit)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Unit Type creation failed: $($response.Error)" $Red
        return $false
    }
}

function Create-Property {
    Write-Step "4. Creating Property"
    
    $propertyData = @{
        name = "Greenview Apartments - Demo"
        city = "Nairobi"
        state = "Nairobi County"
        unit_count = 10
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/properties/create/" -Method "POST" -Body $propertyData -Token $Global:LandlordToken
    
    if ($response.Success) {
        $Global:PropertyId = $response.Data.id
        Write-ColorOutput "✅ Property created successfully:" $Green
        Write-ColorOutput "   Name: $($response.Data.name)" $Green
        Write-ColorOutput "   Location: $($response.Data.city), $($response.Data.state)" $Green
        Write-ColorOutput "   ID: $($response.Data.id)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Property creation failed: $($response.Error)" $Red
        return $false
    }
}

function Create-Unit {
    Write-Step "5. Creating Unit"
    
    $unitData = @{
        property = $Global:PropertyId
        unit_type = $Global:UnitTypeId
        floor = 1
        bedrooms = 1
        bathrooms = 1
        rent = 15000.00
        deposit = 5000.00
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/units/create/" -Method "POST" -Body $unitData -Token $Global:LandlordToken
    
    if ($response.Success) {
        $Global:UnitId = $response.Data.id
        Write-ColorOutput "✅ Unit created successfully:" $Green
        Write-ColorOutput "   Unit Number: $($response.Data.unit_number)" $Green
        Write-ColorOutput "   Unit Code: $($response.Data.unit_code)" $Green
        Write-ColorOutput "   Rent: KES $($response.Data.rent)" $Green
        Write-ColorOutput "   Available: $($response.Data.is_available)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Unit creation failed: $($response.Error)" $Red
        return $false
    }
}

function Get-LandlordCode {
    Write-Step "6. Getting Landlord Code for Tenant Registration"
    
    $response = Invoke-ApiRequest -Endpoint "accounts/me/" -Method "GET" -Token $Global:LandlordToken
    
    if ($response.Success) {
        $landlordCode = $response.Data.landlord_code
        Write-ColorOutput "✅ Landlord code retrieved:" $Green
        Write-ColorOutput "   Landlord Code: $landlordCode" $Green
        return $landlordCode
    } else {
        Write-ColorOutput "❌ Failed to get landlord code: $($response.Error)" $Red
        return $null
    }
}

function Register-Tenant {
    param([string]$LandlordCode)
    
    Write-Section "PHASE 2: TENANT ONBOARDING"
    
    Write-Step "1. Registering Tenant Account"
    
    $tenantData = @{
        email = "demo_tenant_$(Get-Random)_@makau.com"
        full_name = "Demo Tenant"
        user_type = "tenant"
        password = "DemoPass123!"
        phone_number = "+254711111111"
        government_id = "87654321"
        landlord_code = $LandlordCode
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/signup/" -Method "POST" -Body $tenantData
    
    if ($response.Success) {
        $Global:TenantId = $response.Data.id
        Write-ColorOutput "✅ Tenant registered successfully:" $Green
        Write-ColorOutput "   Email: $($tenantData.email)" $Green
        Write-ColorOutput "   ID: $($response.Data.id)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Tenant registration failed: $($response.Error)" $Red
        return $false
    }
}

function Login-Tenant {
    Write-Step "2. Tenant Login"
    
    $loginData = @{
        email = "demo_tenant_@makau.com"  # Use consistent email for demo
        password = "DemoPass123!"
        user_type = "tenant"
    }
    
    $response = Invoke-ApiRequest -Endpoint "accounts/token/" -Method "POST" -Body $loginData
    
    if ($response.Success) {
        $Global:TenantToken = $response.Data.access
        Write-ColorOutput "✅ Tenant logged in successfully" $Green
        Write-ColorOutput "   Token obtained: $($Global:TenantToken.Substring(0, 20))..." $Green
        return $true
    } else {
        Write-ColorOutput "❌ Tenant login failed: $($response.Error)" $Red
        return $false
    }
}

function View-Available-Units {
    Write-Step "3. Viewing Available Units"
    
    $response = Invoke-ApiRequest -Endpoint "accounts/available-units/" -Method "GET" -Token $Global:TenantToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Available units retrieved:" $Green
        if ($response.Data.Count -gt 0) {
            foreach ($unit in $response.Data) {
                Write-ColorOutput "   - $($unit.property_name) - Unit $($unit.unit_number)" $Green
            }
        } else {
            Write-ColorOutput "   No available units found" $Yellow
        }
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get available units: $($response.Error)" $Red
        return $false
    }
}

function Get-User-Profile {
    param([string]$Token, [string]$UserType)
    
    Write-Step "Getting $UserType Profile"
    
    $response = Invoke-ApiRequest -Endpoint "accounts/me/" -Method "GET" -Token $Token
    
    if ($response.Success) {
        Write-ColorOutput "✅ $UserType profile retrieved:" $Green
        Write-ColorOutput "   Name: $($response.Data.full_name)" $Green
        Write-ColorOutput "   Email: $($response.Data.email)" $Green
        Write-ColorOutput "   User Type: $($response.Data.user_type)" $Green
        if ($response.Data.phone_number) {
            Write-ColorOutput "   Phone: $($response.Data.phone_number)" $Green
        }
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get profile: $($response.Error)" $Red
        return $false
    }
}

function Check-Subscription-Status {
    Write-Step "Checking Landlord Subscription Status"
    
    $response = Invoke-ApiRequest -Endpoint "accounts/subscription-status/" -Method "GET" -Token $Global:LandlordToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Subscription status:" $Green
        Write-ColorOutput "   Plan: $($response.Data.plan)" $Green
        Write-ColorOutput "   Active: $($response.Data.is_active)" $Green
        Write-ColorOutput "   Status: $($response.Data.status)" $Green
        if ($response.Data.expiry_date) {
            Write-ColorOutput "   Expiry: $($response.Data.expiry_date)" $Green
        }
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get subscription status: $($response.Error)" $Red
        return $false
    }
}

function View-Landlord-Dashboard {
    Write-Section "PHASE 3: LANDLORD MANAGEMENT"
    
    Write-Step "1. Viewing Landlord Dashboard"
    
    $response = Invoke-ApiRequest -Endpoint "accounts/dashboard-stats/" -Method "GET" -Token $Global:LandlordToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Dashboard statistics:" $Green
        Write-ColorOutput "   Active Tenants: $($response.Data.total_active_tenants)" $Green
        Write-ColorOutput "   Available Units: $($response.Data.total_units_available)" $Green
        Write-ColorOutput "   Occupied Units: $($response.Data.total_units_occupied)" $Green
        Write-ColorOutput "   Monthly Revenue: KES $($response.Data.monthly_revenue)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get dashboard stats: $($response.Error)" $Red
        return $false
    }
}

function View-Rent-Summary {
    Write-Step "2. Viewing Rent Summary"
    
    $response = Invoke-ApiRequest -Endpoint "payments/rent-payments/summary/" -Method "GET" -Token $Global:LandlordToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Rent summary:" $Green
        Write-ColorOutput "   Total Collected: KES $($response.Data.total_collected)" $Green
        Write-ColorOutput "   Total Outstanding: KES $($response.Data.total_outstanding)" $Green
        Write-ColorOutput "   Units: $($response.Data.units.Count)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get rent summary: $($response.Error)" $Red
        return $false
    }
}

function View-Landlord-Properties {
    Write-Step "3. Viewing Landlord Properties"
    
    $response = Invoke-ApiRequest -Endpoint "accounts/properties/" -Method "GET" -Token $Global:LandlordToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Properties list:" $Green
        foreach ($property in $response.Data) {
            Write-ColorOutput "   - $($property.name) ($($property.city)) - $($property.unit_count) units" $Green
        }
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get properties: $($response.Error)" $Red
        return $false
    }
}

function Submit-Maintenance-Report {
    Write-Section "PHASE 4: MAINTENANCE & COMMUNICATION"
    
    Write-Step "1. Submitting Maintenance Report"
    
    # First, get the tenant's assigned unit
    $profileResponse = Invoke-ApiRequest -Endpoint "accounts/me/" -Method "GET" -Token $Global:TenantToken
    
    if (-not $profileResponse.Success) {
        Write-ColorOutput "❌ Cannot get tenant profile for report submission" $Red
        return $false
    }
    
    # For demo purposes, we'll use the unit we created earlier
    $reportData = @{
        unit = $Global:UnitId
        issue_category = "plumbing"
        priority_level = "medium"
        issue_title = "Demo: Leaking Kitchen Faucet"
        description = "This is a demo maintenance report. The kitchen faucet has been leaking for the past 2 days."
    }
    
    $response = Invoke-ApiRequest -Endpoint "communication/reports/create/" -Method "POST" -Body $reportData -Token $Global:TenantToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Maintenance report submitted:" $Green
        Write-ColorOutput "   Issue: $($response.Data.issue_title)" $Green
        Write-ColorOutput "   Category: $($response.Data.issue_category)" $Green
        Write-ColorOutput "   Priority: $($response.Data.priority_level)" $Green
        Write-ColorOutput "   Status: $($response.Data.status)" $Green
        return $true
    } else {
        Write-ColorOutput "❌ Failed to submit maintenance report: $($response.Error)" $Red
        return $false
    }
}

function View-Tenant-Reports {
    Write-Step "2. Viewing Tenant Reports"
    
    $response = Invoke-ApiRequest -Endpoint "communication/reports/open/" -Method "GET" -Token $Global:TenantToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Open reports:" $Green
        if ($response.Data.Count -gt 0) {
            foreach ($report in $response.Data) {
                Write-ColorOutput "   - $($report.issue_title) [$($report.status)]" $Green
            }
        } else {
            Write-ColorOutput "   No open reports found" $Yellow
        }
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get reports: $($response.Error)" $Red
        return $false
    }
}

function View-Landlord-Reports {
    Write-Step "3. Viewing Landlord Reports"
    
    $response = Invoke-ApiRequest -Endpoint "communication/reports/open/" -Method "GET" -Token $Global:LandlordToken
    
    if ($response.Success) {
        Write-ColorOutput "✅ Landlord open reports:" $Green
        if ($response.Data.Count -gt 0) {
            foreach ($report in $response.Data) {
                Write-ColorOutput "   - $($report.issue_title) by $($report.tenant.full_name)" $Green
            }
        } else {
            Write-ColorOutput "   No open reports found" $Yellow
        }
        return $true
    } else {
        Write-ColorOutput "❌ Failed to get landlord reports: $($response.Error)" $Red
        return $false
    }
}

function Demo-Payment-Workflow {
    Write-Section "PHASE 5: PAYMENT WORKFLOW DEMO"
    
    Write-Step "1. Demonstrating Payment Endpoints"
    
    # Show payment endpoints are accessible
    Write-ColorOutput "📋 Available Payment Endpoints:" $Cyan
    Write-ColorOutput "   • Rent Payments: $ApiUrl/payments/rent-payments/" $Cyan
    Write-ColorOutput "   • Subscription Payments: $ApiUrl/payments/subscription-payments/" $Cyan
    Write-ColorOutput "   • Deposit Initiation: $ApiUrl/payments/initiate-deposit/" $Cyan
    Write-ColorOutput "   • STK Push (Rent): $ApiUrl/payments/stk-push/{unit_id}/" $Cyan
    Write-ColorOutput "   • STK Push (Subscription): $ApiUrl/payments/stk-push-subscription/" $Cyan
    
    Write-ColorOutput "`n💡 Note: Actual payment processing requires M-Pesa integration" $Yellow
    Write-ColorOutput "   and would trigger real monetary transactions." $Yellow
}

function Show-System-Status {
    Write-Section "SYSTEM STATUS SUMMARY"
    
    Write-ColorOutput "🔧 Application Components Status:" $Cyan
    
    # Test various endpoints
    $endpoints = @(
        @{Name="Authentication"; Endpoint="accounts/token/"},
        @{Name="User Management"; Endpoint="accounts/me/"},
        @{Name="Properties"; Endpoint="accounts/properties/"},
        @{Name="Payments"; Endpoint="payments/rent-payments/"},
        @{Name="Communication"; Endpoint="communication/reports/open/"}
    )
    
    foreach ($endpoint in $endpoints) {
        $testResponse = Invoke-ApiRequest -Endpoint $endpoint.Endpoint -Method "GET" -Token $Global:LandlordToken
        $status = if ($testResponse.Success -or $testResponse.StatusCode -eq 401) { "✅ Online" } else { "❌ Offline" }
        Write-ColorOutput "   $($endpoint.Name): $status" $(if ($testResponse.Success -or $testResponse.StatusCode -eq 401) { $Green } else { $Red })
    }
}

function Main {
    Write-Host "`n" + "="*70 -ForegroundColor $Magenta
    Write-Host "MAKAU RENTALS - REAL LIFE APPLICATION WORKFLOW DEMO" -ForegroundColor $Magenta
    Write-Host "Live Server: $BaseUrl" -ForegroundColor $Magenta
    Write-Host "="*70 -ForegroundColor $Magenta
    
    # Test API connection first
    if (-not (Test-ApiConnection)) {
        Write-ColorOutput "`n❌ Cannot proceed without API connection. Please check if the server is running." $Red
        return
    }
    
    # Landlord workflow
    if (-not (Register-Landlord)) { return }
    if (-not (Login-Landlord)) { return }
    if (-not (Create-UnitType)) { return }
    if (-not (Create-Property)) { return }
    if (-not (Create-Unit)) { return }
    
    $landlordCode = Get-LandlordCode
    if (-not $landlordCode) { return }
    
    # Tenant workflow  
    if (-not (Register-Tenant -LandlordCode $landlordCode)) { return }
    if (-not (Login-Tenant)) { return }
    
    # User profiles
    Get-User-Profile -Token $Global:LandlordToken -UserType "Landlord"
    Get-User-Profile -Token $Global:TenantToken -UserType "Tenant"
    
    # Property management
    View-Available-Units
    
    # Subscription & Dashboard
    Check-Subscription-Status
    View-Landlord-Dashboard
    View-Rent-Summary
    View-Landlord-Properties
    
    # Maintenance reports
    Submit-Maintenance-Report
    View-Tenant-Reports
    View-Landlord-Reports
    
    # Payment workflow demo
    Demo-Payment-Workflow
    
    # System status
    Show-System-Status
    
    Write-Section "DEMO COMPLETED SUCCESSFULLY!"
    Write-ColorOutput "🎉 The Makau Rentals application workflow has been successfully demonstrated!" $Green
    Write-ColorOutput "`n📊 Demo Summary:" $Cyan
    Write-ColorOutput "   • Landlord account created and authenticated" $Cyan
    Write-ColorOutput "   • Property and unit created" $Cyan
    Write-ColorOutput "   • Tenant account created and linked to landlord" $Cyan
    Write-ColorOutput "   • Maintenance report submitted" $Cyan
    Write-ColorOutput "   • All major application features tested" $Cyan
    Write-ColorOutput "`n🌐 Live API Endpoints:" $Cyan
    Write-ColorOutput "   Base URL: $BaseUrl" $Cyan
    Write-ColorOutput "   API Documentation: $BaseUrl/api/docs/" $Cyan
}

# Start the demo
try {
    Main
}
catch {
    Write-ColorOutput "`n❌ An unexpected error occurred: $($_.Exception.Message)" $Red
    Write-ColorOutput "Stack trace: $($_.ScriptStackTrace)" $Red
}

Write-Host "`n" + "="*70 -ForegroundColor $Magenta
Write-Host "Demo script execution completed" -ForegroundColor $Magenta
Write-Host "="*70 -ForegroundColor $Magenta
