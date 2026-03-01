import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

def send_email(to_email: str, subject: str, html_content: str):
    """
    Sends an email using the configured SMTP server.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print(f"⚠️ SMTP not configured. Mocking email to {to_email}")
        print(f"Subject: {subject}")
        print(f"Content: {html_content[:50]}...")
        return

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = to_email

        part = MIMEText(html_content, "html")
        message.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, to_email, message.as_string())
            
        print(f"✅ Email sent successfully to {to_email}")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        logging.error(f"Failed to send email: {e}")

def send_verification_email(to_email: str, code: str):
    subject = "RheXa Security Protocol: Verification Code"
    html_content = f"""
    <html>
        <body style="background-color: #000; color: #fff; font-family: monospace; padding: 20px;">
            <div style="border: 1px solid #333; padding: 30px; max-width: 600px; margin: 0 auto;">
                <h1 style="color: #ff0000; text-transform: uppercase; letter-spacing: 5px; font-size: 24px; border-bottom: 1px solid #ff0000; padding-bottom: 10px;">RheXa Intelligence</h1>
                <p style="color: #888;">SECURITY PROTOCOL: VERIFICATION_SEQUENCE_INITIATED</p>
                <br/>
                <p>Identity verification required for terminal access.</p>
                <p>Use the following secure transmission sequence to finalize your link:</p>
                <br/>
                <div style="background: #111; border: 1px solid #ff0000; color: #ff0000; font-size: 32px; letter-spacing: 10px; text-align: center; padding: 20px; font-weight: bold;">
                    {code}
                </div>
                <br/>
                <p style="font-size: 12px; color: #555;">This protocol will expire in 15 minutes.</p>
                <p style="font-size: 12px; color: #555;">// END TRANSMISSION</p>
            </div>
        </body>
    </html>
    """
    send_email(to_email, subject, html_content)


def send_password_reset_email(to_email: str, code: str):
    subject = "RheXa Security Protocol: Password Reset Sequence"
    html_content = f"""
    <html>
        <body style="background-color: #000; color: #fff; font-family: monospace; padding: 20px;">
            <div style="border: 1px solid #333; padding: 30px; max-width: 600px; margin: 0 auto;">
                <h1 style="color: #00f0ff; text-transform: uppercase; letter-spacing: 5px; font-size: 24px; border-bottom: 1px solid #00f0ff; padding-bottom: 10px;">RheXa Intelligence</h1>
                <p style="color: #888;">SECURITY PROTOCOL: PASSWORD_RESET_SEQUENCE_INITIATED</p>
                <br/>
                <p>Identity verification required for password override.</p>
                <p>Use the following secure transmission sequence to proceed with the reset:</p>
                <br/>
                <div style="background: #111; border: 1px solid #00f0ff; color: #00f0ff; font-size: 32px; letter-spacing: 10px; text-align: center; padding: 20px; font-weight: bold;">
                    {code}
                </div>
                <br/>
                <p style="font-size: 12px; color: #555;">This protocol will expire in 15 minutes.</p>
                <p style="font-size: 12px; color: #555;">If you did not initiate this sequence, please alert your administrator immediately.</p>
                <p style="font-size: 12px; color: #555;">// END TRANSMISSION</p>
            </div>
        </body>
    </html>
    """
    send_email(to_email, subject, html_content)
