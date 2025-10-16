#!/usr/bin/env python
import os
import django
import sys

def run_tests():
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    
    # Setup Django
    django.setup()
    
    # Run the specific test
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)
    
    # Run only the integration test
    failures = test_runner.run_tests(['tests.integration_test'])
    
    return failures

if __name__ == '__main__':
    failures = run_tests()
    sys.exit(bool(failures))
