# Virtual Room 360

**CHANGE SENDER EMAIL FOR OTP**

The email "FROM" address is configured within the environment file, alongside the SMTP credentials...
  Glad to hear it's working!
To change the sender email to your new official email ID, you only need to update the settings in your **.env** file. You do not need to touch any code.


### Step 1: Open .env and Update the Variables

Depending on what service your official email uses, update .env:

#### Scenario A: Your Official Email is on Google Workspace / Gmail (e.g., support@yourdomain.com or official@gmail.com)

1. Log into your official email account.
2. Go to Google Account → Security → Enable 2-Step Verification.
3. Generate an App Password for that official account.
4. Update .env:
	SMTP_HOST=smtp.gmail.com
	SMTP_PORT=465
	SMTP_USERNAME=support@yourdomain.com
	SMTP_PASSWORD=your_new_16_char_app_password
	SMTP_FROM=support@yourdomain.com
	SMTP_USE_TLS=false
	SMTP_USE_SSL=true

#### Scenario B: Your Official Email is on a Custom Domain via a Service (Brevo, SendGrid, Amazon SES, Zoho, etc.)

If you host your domain's email with a transactional email provider (like Brevo, SendGrid, or Amazon SES):

1. Verify your official email address (e.g. noreply@yourdomain.com) in their dashboard.
2. Update .env with their SMTP host and credentials:
	SMTP_HOST=smtp-relay.brevo.com
	SMTP_PORT=587
	SMTP_USERNAME=your_provider_username_or_api_key
	SMTP_PASSWORD=your_provider_password_or_secret
	SMTP_FROM=noreply@yourdomain.com
	SMTP_USE_TLS=true
	SMTP_USE_SSL=false

### Bonus Tip: Adding a Friendly Brand Name

You can also include your brand name so recipients see 360 Rooms <support@yourdomain.com> in their inbox:

```env
SMTP_FROM="360 Rooms" <support@yourdomain.com>
```
> **Note**  
> Because `email_service.py` automatically reloads `.env`, any changes immediately for the very next OTP request.
