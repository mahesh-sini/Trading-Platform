import os
import logging
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import asyncio

logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@tradingplatform.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Jinja2 template environment
template_env = Environment(loader=FileSystemLoader("templates/email"))

class EmailService:
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.username = SMTP_USERNAME
        self.password = SMTP_PASSWORD
        self.from_email = FROM_EMAIL

    def _create_connection(self):
        """Create SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {str(e)}")
            raise

    def _send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """Send email with HTML and optional text content"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Add text version if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                msg.attach(text_part)

            # Add HTML version
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send email
            with self._create_connection() as server:
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_verification_email(self, email: str, first_name: str, verification_token: str):
        """Send email verification email"""
        try:
            verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"
            
            # Load template
            template = template_env.get_template("verification.html")
            html_content = template.render(
                first_name=first_name,
                verification_url=verification_url,
                platform_name="AI Trading Platform"
            )
            
            # Text fallback
            text_content = f"""
            Hi {first_name},
            
            Welcome to AI Trading Platform! Please verify your email address by clicking the link below:
            
            {verification_url}
            
            If you didn't create an account, you can safely ignore this email.
            
            Best regards,
            AI Trading Platform Team
            """
            
            subject = "Verify Your Email - AI Trading Platform"
            
            return self._send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            return False

    def send_password_reset_email(self, email: str, first_name: str, reset_token: str):
        """Send password reset email"""
        try:
            reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"
            
            # Load template
            template = template_env.get_template("password_reset.html")
            html_content = template.render(
                first_name=first_name,
                reset_url=reset_url,
                platform_name="AI Trading Platform"
            )
            
            # Text fallback
            text_content = f"""
            Hi {first_name},
            
            You requested a password reset for your AI Trading Platform account. Click the link below to reset your password:
            
            {reset_url}
            
            This link will expire in 1 hour. If you didn't request this reset, you can safely ignore this email.
            
            Best regards,
            AI Trading Platform Team
            """
            
            subject = "Reset Your Password - AI Trading Platform"
            
            return self._send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False

    def send_welcome_email(self, email: str, first_name: str):
        """Send welcome email after successful verification"""
        try:
            dashboard_url = f"{FRONTEND_URL}/dashboard"
            
            # Load template
            template = template_env.get_template("welcome.html")
            html_content = template.render(
                first_name=first_name,
                dashboard_url=dashboard_url,
                platform_name="AI Trading Platform"
            )
            
            # Text fallback
            text_content = f"""
            Hi {first_name},
            
            Welcome to AI Trading Platform! Your account has been successfully verified.
            
            You can now access your dashboard at: {dashboard_url}
            
            Get started by:
            1. Connecting your broker account
            2. Creating your first watchlist
            3. Exploring AI-powered predictions
            
            Best regards,
            AI Trading Platform Team
            """
            
            subject = "Welcome to AI Trading Platform!"
            
            return self._send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False

    def send_subscription_confirmation(self, email: str, first_name: str, plan_name: str, amount: float):
        """Send subscription confirmation email"""
        try:
            dashboard_url = f"{FRONTEND_URL}/dashboard"
            
            # Load template
            template = template_env.get_template("subscription_confirmation.html")
            html_content = template.render(
                first_name=first_name,
                plan_name=plan_name,
                amount=amount,
                dashboard_url=dashboard_url,
                platform_name="AI Trading Platform"
            )
            
            # Text fallback
            text_content = f"""
            Hi {first_name},
            
            Your subscription to {plan_name} has been confirmed!
            
            Plan: {plan_name}
            Amount: ${amount:.2f}
            
            You can access all your new features at: {dashboard_url}
            
            Best regards,
            AI Trading Platform Team
            """
            
            subject = f"Subscription Confirmed - {plan_name}"
            
            return self._send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send subscription confirmation email: {str(e)}")
            return False

# Create singleton instance
email_service = EmailService()

# Async wrapper functions for background tasks
async def send_verification_email(email: str, first_name: str, verification_token: str):
    """Async wrapper for sending verification email"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        email_service.send_verification_email, 
        email, 
        first_name, 
        verification_token
    )

async def send_password_reset_email(email: str, first_name: str, reset_token: str):
    """Async wrapper for sending password reset email"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        email_service.send_password_reset_email, 
        email, 
        first_name, 
        reset_token
    )

async def send_welcome_email(email: str, first_name: str):
    """Async wrapper for sending welcome email"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        email_service.send_welcome_email, 
        email, 
        first_name
    )

async def send_subscription_confirmation(email: str, first_name: str, plan_name: str, amount: float):
    """Async wrapper for sending subscription confirmation email"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        email_service.send_subscription_confirmation, 
        email, 
        first_name, 
        plan_name, 
        amount
    )