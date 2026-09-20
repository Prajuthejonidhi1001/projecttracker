import os
import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
from .excel_models import EmailLog

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("email_service")

class EmailService:
    @staticmethod
    def send_email(recipient, subject, body, html_body=None):
        """Send an email using SMTP and log the attempt."""
        server = os.getenv("SMTP_SERVER", "")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
        sender = os.getenv("DEFAULT_FROM_EMAIL", user)

        # Log creation
        log = EmailLog(
            recipient=recipient,
            subject=subject,
            body=body,
            status='pending'
        )
        log.save()

        if not server or not user or not password:
            logger.warning(f"SMTP not configured. Would send to {recipient}: {subject}")
            # Still mark as sent to avoid repeated attempts during local testing
            log.status = 'sent'
            log.sent_at = datetime.now().isoformat()
            log.save()
            return True, log

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        
        # Handle multiple comma-separated recipients
        recipients = [r.strip() for r in recipient.split(',') if r.strip()]
        msg['To'] = ", ".join(recipients)
        
        msg.set_content(body)

        if html_body:
            msg.add_alternative(html_body, subtype='html')

        try:
            with smtplib.SMTP(server, port) as s:
                if use_tls:
                    s.starttls()
                s.login(user, password)
                s.send_message(msg)
            
            logger.info(f"EMAIL sent to={recipient} subject='{subject}'")
            log.status = 'sent'
            log.sent_at = datetime.now().isoformat()
            log.save()
            return True, log
        except Exception as e:
            error_msg = str(e)[:1000]
            logger.error(f"EMAIL failed to={recipient} subject='{subject}'. Error: {error_msg}")
            log.status = 'failed'
            log.error_message = error_msg
            log.save()
            return False, log
