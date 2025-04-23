import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_emails: list[str], subject: str, body: str):
    # Configuración del servidor SMTP
    smtp_server = "smtp.gmail.com"  # Cambia esto según tu proveedor de correo
    smtp_port = 587
    sender_email = "tu_correo@gmail.com"  # Cambia esto por tu correo
    sender_password = "tu_contraseña"  # Cambia esto por tu contraseña

    # Crear el mensaje de correo
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_emails)  # Convertir la lista de correos en una cadena separada por comas
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Enviar el correo
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_emails, msg.as_string())
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
