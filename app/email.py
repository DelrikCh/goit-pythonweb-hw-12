import os
import smtplib

from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()


def send_email(receiver_email, subject, body):
    sender_email = os.getenv("ENV_EMAIL")
    sender_password = os.getenv("ENV_EMAIL_PASSWORD")
    print(f"email: {sender_email}")
    print(f"password: {sender_password}")
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()  # Upgrade connection to secure
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()
