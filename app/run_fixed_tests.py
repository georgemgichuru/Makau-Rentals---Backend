# run_fixed_tests.py
#!/usr/bin/env python
import os
import sys
import django
import subprocess

def run_fixed_tests():
    """Run fixed test suites with correct URLs"""
    
    print("=== MAKAU RENTALS FIXED TEST SUITE ===")
    
    # Run tests in order
    test_suites = [
        "accounts.tests_subscription",
        "payments.tests.PaymentModelTests",
        "payments.tests.SubscriptionPaymentModelTests",
        "payments.tests.PaymentViewTests", 
        "payments.tests.SubscriptionPaymentViewTests",
        "payments.tests.MPESACallbackTests",
        "communication.tests.ReportModelTests",
        "communication.tests.ReportViewTests",
    ]
    
    all_passed = True
    
    for test_suite in test_suites:
        print(f"\n{'='*60}")
        print(f"RUNNING: {test_suite}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(
                ['python', 'manage.py', 'test', test_suite, '--verbosity=2'],
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            if result.returncode != 0:
                all_passed = False
                print(f"❌ {test_suite} FAILED")
            else:
                print(f"✅ {test_suite} PASSED")
                
        except Exception as e:
            print(f"❌ Error running {test_suite}: {e}")
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("💥 SOME TESTS FAILED - Check individual test results")
    print(f"{'='*60}")  # FIXED: Changed from '='=60 to '='*60
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    django.setup()
    sys.exit(run_fixed_tests())