import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
import logging

logger = logging.getLogger(__name__)

def generate_access_token():
    """
    Generate M-Pesa access token with error handling.
    Returns token string or raises ValueError on failure.
    """
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        raise ValueError("MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be set in settings.")

    # Use sandbox or production URL based on env
    base_url = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"
    url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=10  # Avoid hanging
        )
        response.raise_for_status()  # Raise on HTTP errors (e.g., 401 Unauthorized)

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ValueError(f"No access_token in response: {data}")

        logger.info("M-Pesa access token generated successfully.")
        return token

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate M-Pesa token: {e}")
        raise ValueError(f"Token generation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error generating token: {e}")
        raise ValueError(f"Token generation error: {str(e)}")
