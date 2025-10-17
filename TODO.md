# TODO: Modify test.ps1 for Comprehensive Workflow Testing

## Approved Plan
- Modify existing test.ps1 to include tests for M-Pesa integration, Disbursements feature, Report system, and validate all endpoints for correct JSON input/output.
- Ensure real-life scenario robustness with error handling and status checks.

## Steps to Complete
- [x] Add new section for Disbursements testing (e.g., payments/disbursements/ endpoint).
- [x] Expand Report system tests to include payment reports, tenant reports, landlord reports, etc.
- [x] Add comprehensive endpoint testing for all major APIs (accounts, payments, communication) with JSON validation.
- [x] Include error handling and status checks for real-life robustness.
- [x] Keep M-Pesa tests with 1 KSH amounts.
- [x] Integrate new functions into the Main workflow.
- [ ] Run the modified script to test live API.
- [ ] Check console output for successes/failures and verify M-Pesa transactions.
- [ ] Validate JSON responses against expected schemas.
- [ ] Handle any errors or missing endpoints by logging and continuing.
- [x] Final review: Ensure script covers all endpoints and real-life scenarios.

## Dependent Files
- test.ps1 (already modified)

## Followup Steps
- Execute the script in PowerShell.
- Monitor for API errors or timeouts.
- Check phone for M-Pesa confirmations.
- If issues arise, debug and re-edit script.
