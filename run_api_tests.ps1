# Instead of running the .ps1 file, run this directly in PowerShell
Write-Host "=== MAKAU RENTALS API TEST SUITE ===" -ForegroundColor Yellow

# Run Django tests in Docker
Write-Host "`n1. Running Subscription Tests..." -ForegroundColor Green
docker-compose exec web python manage.py test accounts.tests_subscription --verbosity=2

Write-Host "`n2. Running Payment Tests..." -ForegroundColor Green
docker-compose exec web python manage.py test payments.tests --verbosity=2

Write-Host "`n3. Running Report Tests..." -ForegroundColor Green
docker-compose exec web python manage.py test communication.tests --verbosity=2

Write-Host "`n4. Running All Tests Together..." -ForegroundColor Green
docker-compose exec web python manage.py test accounts.tests_subscription payments.tests communication.tests --verbosity=2

Write-Host "`n=== TESTING COMPLETE ===" -ForegroundColor Yellow