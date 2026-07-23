import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def send_otp_email(to_email: str, otp: str, ttl_minutes: int) -> None:
    host = os.getenv("MAIL_HOST")
    port = int(os.getenv("MAIL_PORT", "465"))
    user = os.getenv("MAIL_USER")
    password = os.getenv("MAIL_P")
    secure = os.getenv("MAIL_SECURE", "true").lower() == "true"
    from_email = os.getenv("MAIL_FROM", user)
    from_name = os.getenv("MAIL_FROM_NAME", "AgroHub")

    if not host or not user or not password:
        raise RuntimeError("MAIL_HOST/MAIL_USER/MAIL_P no configurados en el servidor")

    message = MIMEText(
        f"Tu código para restablecer tu contraseña en AgroHub es: {otp}\n\n"
        f"Este código vence en {ttl_minutes} minutos. Si no solicitaste este cambio, ignora este mensaje."
    )
    message["Subject"] = "Código para restablecer tu contraseña — AgroHub"
    message["From"] = formataddr((from_name, from_email))
    message["To"] = to_email

    if secure:
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.login(user, password)
            server.sendmail(from_email, [to_email], message.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_email, [to_email], message.as_string())
