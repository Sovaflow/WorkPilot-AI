"""Optional SMTP delivery; never called without --send."""
import os
import smtplib
from email.message import EmailMessage


def send(subject, body):
    required = ["WORKPILOT_SMTP_HOST", "WORKPILOT_SMTP_USER",
                "WORKPILOT_SMTP_PASSWORD", "WORKPILOT_RECIPIENT"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing SMTP environment variables: " + ", ".join(missing))
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["WORKPILOT_SMTP_USER"]
    msg["To"] = os.environ["WORKPILOT_RECIPIENT"]
    msg.set_content(body)
    with smtplib.SMTP(os.environ["WORKPILOT_SMTP_HOST"],
                      int(os.getenv("WORKPILOT_SMTP_PORT", "587")), timeout=15) as server:
        server.starttls()
        server.login(os.environ["WORKPILOT_SMTP_USER"], os.environ["WORKPILOT_SMTP_PASSWORD"])
        server.send_message(msg)
