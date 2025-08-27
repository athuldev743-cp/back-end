# routes/email_util.py
import smtplib, ssl, os, random
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load env vars
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


# ---------- OTP Generator ----------
def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP with given length (default 6 digits)."""
    return "".join([str(random.randint(0, 9)) for _ in range(length)])


# ---------- Email Sender ----------
def send_email(to_email: str, subject: str, message: str) -> bool:
    """Send an email via SMTP with TLS."""
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print("❌ Email failed:", e)
        return False


# ---------- OTP Mail Wrapper ----------
def send_otp_email(to_email: str, otp: str) -> bool:
    """Send a formatted OTP email."""
    subject = "Your OTP Code for Estateuro"
    body = f"""
Hello,

Your OTP code is: {otp}

⚠️ This code will expire in 5 minutes.

Thank you,  
Estateuro Team
"""
    return send_email(to_email, subject, body)
