# Required Environment Variables for Render Deployment

## Database Configuration
- `POSTGRES_DB`: PostgreSQL database name
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `DB_HOST`: Database host (provided by Render)

## Django Configuration
- `SECRET_KEY`: Django secret key (generate a secure random string)
- `DEBUG`: Set to `False` for production
- `DJANGO_SUPERUSER_USERNAME`: Superuser username for auto-creation
- `DJANGO_SUPERUSER_EMAIL`: Superuser email
- `DJANGO_SUPERUSER_PASSWORD`: Superuser password

## M-Pesa Configuration (Sandbox)
- `MPESA_ENV`: Set to `sandbox` for testing, `production` for live
- `MPESA_CONSUMER_KEY`: M-Pesa consumer key from Safaricom
- `MPESA_CONSUMER_SECRET`: M-Pesa consumer secret from Safaricom
- `MPESA_SHORTCODE`: Your M-Pesa shortcode
- `MPESA_PASSKEY`: M-Pesa passkey for STK push
- `MPESA_INITIATOR_NAME`: Initiator name for B2C payments
- `MPESA_SECURITY_CREDENTIAL`: Security credential for B2C payments

## M-Pesa Callback URLs
- `MPESA_CALLBACK_URL`: Base callback URL (your Render app URL)
- `MPESA_RENT_CALLBACK_URL`: Specific URL for rent payments
- `MPESA_SUBSCRIPTION_CALLBACK_URL`: Specific URL for subscriptions
- `MPESA_DEPOSIT_CALLBACK_URL`: Specific URL for deposits
- `MPESA_B2C_RESULT_URL`: B2C result callback URL
- `MPESA_B2C_TIMEOUT_URL`: B2C timeout callback URL

## Redis/Celery (Optional for Render)
- `REDIS_URL`: Redis URL if using external Redis

## Frontend Configuration
- `FRONTEND_URL`: Your frontend application URL

## File Storage (Optional)
- `USE_S3`: Set to `True` to use AWS S3 for file storage
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_STORAGE_BUCKET_NAME`: S3 bucket name
- `AWS_S3_REGION_NAME`: AWS region
