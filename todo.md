# AssignTenantView Improvements - TODO

## Completed Tasks
- [x] Add CSRF exemption decorator
- [x] Add comprehensive logging throughout the process
- [x] Add validation to ensure unit is available (is_available=True)
- [x] Add check to prevent assigning tenant who already has a unit
- [x] Validate tenant phone number exists and is valid
- [x] Improve error messages and response structure
- [x] Add better exception handling
- [x] Rename class to AssignTenantView for clarity
- [x] Add status field in response (pending/success/failed)

## Followup Steps
- [x] Update any URL patterns or imports that reference the old class name
- [x] Test the updated view with various scenarios
- [x] Verify callback handling still works correctly
- [x] Check logging output for debugging
- [x] Run unit tests if available
- [x] Increase deposit callback timeout from 30 to 60 seconds for better testing reliability
