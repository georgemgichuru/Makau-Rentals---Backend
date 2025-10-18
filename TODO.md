CHANGE THIS

#TODO: change hardcoded values THIS IS JUST FOR TESTING !!!!
        payload = {
            "BusinessShortCode": 174379,#settings.MPESA_SHORTCODE,
            "Password": 'Safaricom123!!',#password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": 600986,#phone_number,
            "PartyB": 600000,#settings.MPESA_SHORTCODE,
            "PhoneNumber": 254708374149,#phone_number,
            "CallBackURL": settings.MPESA_DEPOSIT_CALLBACK_URL,
            "AccountReference": f"Deposit-{unit.unit_code}",
            "TransactionDesc": f"Deposit payment for {unit.unit_number}"
        }