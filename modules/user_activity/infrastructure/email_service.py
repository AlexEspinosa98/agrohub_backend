import os
import smtplib
from email.mime.text import MIMEText


def send_otp_email(to_email: str, otp: str, ttl_minutes: int) -> None:
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if not smtp_email or not smtp_password:
        raise RuntimeError("SMTP_EMAIL/SMTP_APP_PASSWORD no configurados en el servidor")

    message = MIMEText(
        f"Tu código para restablecer tu contraseña en AgroHub es: {otp}\n\n"
        f"Este código vence en {ttl_minutes} minutos. Si no solicitaste este cambio, ignora este mensaje."
    )
    message["Subject"] = "Código para restablecer tu contraseña — AgroHub"
    message["From"] = smtp_email
    message["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, [to_email], message.as_string())
