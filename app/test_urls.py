# test_urls.py
from django.urls import URLPattern, URLResolver
from django.conf import settings
import importlib
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

def print_all_urls():
    """Print all URLs in the project to help debug 404 errors"""
    urlconf = importlib.import_module(settings.ROOT_URLCONF)
    
    def print_urls(urlpatterns, prefix=''):
        for pattern in urlpatterns:
            if isinstance(pattern, URLPattern):
                print(f"{prefix}{pattern.pattern}")
            elif isinstance(pattern, URLResolver):
                print_urls(pattern.url_patterns, prefix + str(pattern.pattern))
    
    print("=== ALL URL PATTERNS ===")
    print_urls(urlconf.urlpatterns)

if __name__ == '__main__':
    print_all_urls()