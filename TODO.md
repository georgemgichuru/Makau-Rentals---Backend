# TODO: Improve test.ps1 Script

## Tasks
- [ ] Add script parameters for configurability (baseUrl, depositAmount, rentAmount, subscriptionAmount, etc.)
- [ ] Create Validate-Response function to check HTTP status and expected fields
- [ ] Modularize script into functions:
  - [ ] Test-LandlordSignup
  - [ ] Test-LandlordLogin
  - [ ] Test-PropertyCreation
  - [ ] Test-UnitTypeCreation
  - [ ] Test-UnitCreation
  - [ ] Test-TenantSignup
  - [ ] Test-TenantLogin
  - [ ] Test-DepositPayment
  - [ ] Test-RentPayment
  - [ ] Test-SubscriptionPayment
  - [ ] Test-ReportCreation
  - [ ] Test-StatsAndSummaries
- [ ] Improve error handling: skip dependent tests on failure, detailed messages
- [ ] Add colored output (green success, red failure), progress indicators
- [ ] Add Test-Cleanup function to delete test data
- [ ] Add test results summary with pass/fail counts
- [ ] Update main script logic to call functions and track results
