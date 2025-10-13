import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
import logging
import base64
import datetime

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

def initiate_b2c_payment(amount, recipient, payment_id, remarks="Rent disbursement"):
    """
    Initiate B2C payment to disburse funds to landlord.
    - amount: Amount to disburse (KES)
    - recipient: Landlord's phone number (254XXXXXXXXX format) or till number
    - payment_id: Reference for the payment
    - remarks: Description of the transaction
    Returns response dict or raises ValueError on failure.
    """
    if not settings.MPESA_CONSUMER_KEY or not settings.MPESA_CONSUMER_SECRET:
        raise ValueError("MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be set in settings.")

    # Generate access token
    access_token = generate_access_token()

    # Use sandbox or production URL based on env
    base_url = "https://sandbox.safaricom.co.ke" if settings.MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"
    url = f"{base_url}/mpesa/b2c/v1/paymentrequest"

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "InitiatorName": settings.MPESA_INITIATOR_NAME,  # Need to add to settings
        "SecurityCredential": settings.MPESA_SECURITY_CREDENTIAL,  # Need to add to settings
        "CommandID": "BusinessPayment",
        "Amount": str(amount),
        "PartyA": settings.MPESA_SHORTCODE,
        "PartyB": recipient,  # Can be phone number or till number
        "Remarks": remarks,
        "QueueTimeOutURL": settings.MPESA_B2C_TIMEOUT_URL,  # Need to add to settings
        "ResultURL": settings.MPESA_B2C_RESULT_URL,  # Need to add to settings
        "Occasion": f"Payment {payment_id}"
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"B2C payment initiated: {data}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"B2C payment failed: {e}")
        raise ValueError(f"B2C payment error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected B2C error: {e}")
        raise ValueError(f"B2C error: {str(e)}")
