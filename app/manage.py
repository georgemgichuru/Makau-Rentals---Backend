#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Check if we should create superuser, but do it AFTER Django setup
    should_create_superuser = len(sys.argv) > 1 and sys.argv[1] in ['runserver', 'migrate']
    
    # Execute Django commands first to ensure apps are loaded
    execute_from_command_line(sys.argv)
    
    # Now create superuser AFTER the command has run
    if should_create_superuser:
        try:
            from django.contrib.auth import get_user_model
            from django.core.management import execute_from_command_line
            
            User = get_user_model()
            
            # Get superuser credentials from environment variables
            superuser_email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
            superuser_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
            
            # Only create superuser if both environment variables are set
            if superuser_email and superuser_password:
                if not User.objects.filter(email=superuser_email).exists():
                    User.objects.create_superuser(
                        email=superuser_email,
                        password=superuser_password
                    )
                    print(f"Superuser created successfully with email: {superuser_email}")
                else:
                    print(f"Superuser with email {superuser_email} already exists")
            else:
                print("Note: Superuser environment variables not set, skipping auto-creation")
                
        except Exception as e:
            print(f"Error creating superuser: {e}")


if __name__ == '__main__':
    main()