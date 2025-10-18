# M-Pesa Callback URLs Configuration

## Where to Get B2C Callback URLs

The `MPESA_B2C_RESULT_URL` and `MPESA_B2C_TIMEOUT_URL` are URLs that you define in your application. These are endpoints that Safaricom's M-Pesa will call when B2C (Business to Customer) transactions complete.

## For Your Render Deployment:

### MPESA_B2C_RESULT_URL
```
https://your-render-app-url.com/payments/callback/b2c/
```

### MPESA_B2C_TIMEOUT_URL
```
https://your-render-app-url.com/payments/callback/b2c/
```

**Note:** Both URLs can be the same since your `mpesa_b2c_callback` function handles both successful and timeout scenarios.

## Example for Render App:
If your Render app URL is `https://makau-rentals.onrender.com`, then:

- `MPESA_B2C_RESULT_URL`: `https://makau-rentals.onrender.com/payments/callback/b2c/`
- `MPESA_B2C_TIMEOUT_URL`: `https://makau-rentals.onrender.com/payments/callback/b2c/`

## Other Callback URLs:

- `MPESA_RENT_CALLBACK_URL`: `https://your-app-url.com/payments/callback/rent/`
- `MPESA_SUBSCRIPTION_CALLBACK_URL`: `https://your-app-url.com/payments/callback/subscription/`
- `MPESA_DEPOSIT_CALLBACK_URL`: `https://your-app-url.com/payments/callback/deposit/`

## Important Notes:

1. **Replace `your-render-app-url.com`** with your actual Render app domain
2. **Include the trailing slash** `/` at the end of URLs
3. **Use HTTPS** - Render provides SSL certificates automatically
4. **These URLs must be publicly accessible** for M-Pesa to reach them
5. **Test the endpoints** are working before configuring in M-Pesa portal

## Testing Callback URLs:

You can test if your callback URLs are working by visiting them in a browser or using curl:

```bash
curl https://your-app-url.com/payments/callback/b2c/
```

You should get a response (even if it's an error, it means the endpoint is reachable).
