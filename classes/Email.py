import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from logger_config import logger


class Email:
    def __init__(self,
                 sender_email,
                 smtp_password,
                 receiver_emails):
        self.sender_email = sender_email
        self.smtp_password = smtp_password
        self.receiver_emails = receiver_emails

    def send_file(self, file_paths: list, subject: str, body: str):
        logger.info(f"Sending {' '.join(file_paths)} email to {' '.join(self.receiver_emails)}.")
        try:
            for receiver_email in self.receiver_emails:
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = receiver_email
                msg['Subject'] = subject

                msg.attach(MIMEText(body, 'plain'))

                for file_path in file_paths:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(file_path)}")
                        msg.attach(part)

                context = ssl.create_default_context()
                with smtplib.SMTP_SSL('smtp.mail.ru', 465, context=context) as server:
                    server.login(self.sender_email, self.smtp_password)
                    server.sendmail(self.sender_email, receiver_email, msg.as_string())
                logger.debug(f'Email sent to {receiver_email}.')
            return True
        except Exception as e:
            logger.error(f'Failed to send email: {e}')
            return False
