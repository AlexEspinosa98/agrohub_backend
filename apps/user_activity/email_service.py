import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from django.conf import settings


def send_otp_email(to_email: str, otp: str, ttl_minutes: int) -> None:
    host = settings.MAIL_HOST
    port = settings.MAIL_PORT
    user = settings.MAIL_USER
    password = settings.MAIL_P
    secure = settings.MAIL_SECURE
    from_email = settings.MAIL_FROM or user
    from_name = settings.MAIL_FROM_NAME

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
