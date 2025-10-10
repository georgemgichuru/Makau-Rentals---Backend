# TODO: Connect Report System Backend and Frontend

## Steps to Complete
- [x] Add API functions in api.js for fetching reports by different statuses (urgent, in-progress, resolved)
- [x] Update AdminReports.jsx to fetch all report statuses, make stats dynamic, and call API when updating report status
- [x] Update TenantReportIssue.jsx to submit reports via the API instead of simulating
- [x] Test the connections by running the app and verifying report creation and status updates work

# TODO: Fix Django Admin Error - Missing communication_report Table

## Steps to Complete
- [x] Generate migrations for communication app: docker-compose exec web python manage.py makemigrations communication
- [x] Apply migrations: docker-compose exec web python manage.py migrate communication
- [x] Verify: Check migration status with docker-compose exec web python manage.py showmigrations communication, model accessible via shell, superuser ready for admin testing
