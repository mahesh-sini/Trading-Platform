import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import json

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class NotificationChannel:
    type: NotificationType
    config: Dict[str, Any]
    enabled: bool = True
    priority_filter: List[NotificationPriority] = None

@dataclass
class Notification:
    title: str
    message: str
    priority: NotificationPriority
    category: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    recipients: List[str] = None

class EmailNotifier:
    """Email notification handler"""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_server = smtp_config.get("server", "localhost")
        self.smtp_port = smtp_config.get("port", 587)
        self.username = smtp_config.get("username")
        self.password = smtp_config.get("password")
        self.use_tls = smtp_config.get("use_tls", True)
        self.from_email = smtp_config.get("from_email", "trading-platform@example.com")
    
    async def send_notification(self, notification: Notification, recipients: List[str]):
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = f"[{notification.priority.value.upper()}] {notification.title}"
            
            # Create HTML body
            html_body = self._create_html_body(notification)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {recipients}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            raise
    
    def _create_html_body(self, notification: Notification) -> str:
        """Create HTML email body"""
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.MEDIUM: "#ffc107",
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.CRITICAL: "#dc3545"
        }
        
        color = priority_colors.get(notification.priority, "#6c757d")
        
        html = f"""
        <html>
        <head></head>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h1 style="margin: 0;">{notification.title}</h1>
                    <p style="margin: 5px 0 0 0;">Priority: {notification.priority.value.upper()}</p>
                </div>
                
                <div style="padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px;">
                    <h2>Message</h2>
                    <p>{notification.message}</p>
                    
                    <h3>Details</h3>
                    <ul>
                        <li><strong>Category:</strong> {notification.category}</li>
                        <li><strong>Timestamp:</strong> {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
                    </ul>
                    
                    {self._format_metadata(notification.metadata)}
                </div>
                
                <div style="padding: 10px; background-color: #f8f9fa; border-radius: 0 0 5px 5px; text-align: center; font-size: 12px; color: #6c757d;">
                    AI Trading Platform - Automated Notification System
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for email display"""
        if not metadata:
            return ""
        
        html = "<h3>Additional Information</h3><ul>"
        for key, value in metadata.items():
            html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        html += "</ul>"
        return html

class SlackNotifier:
    """Slack notification handler"""
    
    def __init__(self, slack_config: Dict[str, Any]):
        self.webhook_url = slack_config.get("webhook_url")
        self.channel = slack_config.get("channel", "#alerts")
        self.username = slack_config.get("username", "Trading Platform")
        self.icon_emoji = slack_config.get("icon_emoji", ":robot_face:")
    
    async def send_notification(self, notification: Notification, recipients: List[str] = None):
        """Send Slack notification"""
        try:
            # Create Slack message
            message = self._create_slack_message(notification)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent successfully")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            raise
    
    def _create_slack_message(self, notification: Notification) -> Dict[str, Any]:
        """Create Slack message payload"""
        priority_colors = {
            NotificationPriority.LOW: "good",
            NotificationPriority.MEDIUM: "warning",
            NotificationPriority.HIGH: "danger",
            NotificationPriority.CRITICAL: "danger"
        }
        
        color = priority_colors.get(notification.priority, "good")
        
        attachment = {
            "color": color,
            "title": notification.title,
            "text": notification.message,
            "fields": [
                {
                    "title": "Priority",
                    "value": notification.priority.value.upper(),
                    "short": True
                },
                {
                    "title": "Category",
                    "value": notification.category,
                    "short": True
                },
                {
                    "title": "Timestamp",
                    "value": notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "short": False
                }
            ],
            "footer": "AI Trading Platform",
            "ts": int(notification.timestamp.timestamp())
        }
        
        # Add metadata fields
        if notification.metadata:
            for key, value in notification.metadata.items():
                attachment["fields"].append({
                    "title": key.replace('_', ' ').title(),
                    "value": str(value),
                    "short": True
                })
        
        return {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [attachment]
        }

class WebhookNotifier:
    """Generic webhook notification handler"""
    
    def __init__(self, webhook_config: Dict[str, Any]):
        self.webhook_url = webhook_config.get("url")
        self.headers = webhook_config.get("headers", {})
        self.auth_token = webhook_config.get("auth_token")
    
    async def send_notification(self, notification: Notification, recipients: List[str] = None):
        """Send webhook notification"""
        try:
            headers = self.headers.copy()
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            payload = {
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "category": notification.category,
                "timestamp": notification.timestamp.isoformat(),
                "metadata": notification.metadata or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, 
                    json=payload, 
                    headers=headers
                ) as response:
                    if response.status in [200, 201, 202]:
                        logger.info("Webhook notification sent successfully")
                    else:
                        logger.error(f"Failed to send webhook notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            raise

class NotificationService:
    """Main notification service orchestrator"""
    
    def __init__(self):
        self.channels: Dict[NotificationType, Any] = {}
        self.notification_history: List[Notification] = []
        self.rate_limits: Dict[str, datetime] = {}
        self.setup_default_channels()
    
    def setup_default_channels(self):
        """Setup default notification channels"""
        # Configure channels based on environment variables or config
        # This would be loaded from configuration
        pass
    
    def add_channel(self, channel_type: NotificationType, config: Dict[str, Any]):
        """Add a notification channel"""
        try:
            if channel_type == NotificationType.EMAIL:
                self.channels[channel_type] = EmailNotifier(config)
            elif channel_type == NotificationType.SLACK:
                self.channels[channel_type] = SlackNotifier(config)
            elif channel_type == NotificationType.WEBHOOK:
                self.channels[channel_type] = WebhookNotifier(config)
            
            logger.info(f"Added {channel_type.value} notification channel")
            
        except Exception as e:
            logger.error(f"Failed to add {channel_type.value} channel: {str(e)}")
    
    async def send_notification(
        self, 
        notification: Notification, 
        channels: List[NotificationType] = None,
        recipients: List[str] = None
    ):
        """Send notification through specified channels"""
        try:
            # Use all available channels if none specified
            if channels is None:
                channels = list(self.channels.keys())
            
            # Check rate limiting
            rate_limit_key = f"{notification.category}_{notification.priority.value}"
            if self._is_rate_limited(rate_limit_key):
                logger.warning(f"Notification rate limited: {rate_limit_key}")
                return
            
            # Store notification
            self.notification_history.append(notification)
            
            # Send through each channel
            send_tasks = []
            for channel_type in channels:
                if channel_type in self.channels:
                    notifier = self.channels[channel_type]
                    if hasattr(notifier, 'send_notification'):
                        task = asyncio.create_task(
                            notifier.send_notification(notification, recipients)
                        )
                        send_tasks.append(task)
            
            # Wait for all notifications to be sent
            if send_tasks:
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                logger.info(f"Notification sent through {success_count}/{len(send_tasks)} channels")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
    
    async def send_alert(self, alert):
        """Send system alert notification"""
        notification = Notification(
            title=f"System Alert: {alert.metric_name}",
            message=alert.message,
            priority=self._map_alert_priority(alert.level),
            category="system_alert",
            timestamp=alert.timestamp,
            metadata={
                "service": alert.service,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "level": alert.level.value
            }
        )
        
        await self.send_notification(notification)
    
    async def send_trading_notification(
        self, 
        title: str, 
        message: str, 
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Dict[str, Any] = None
    ):
        """Send trading-related notification"""
        notification = Notification(
            title=title,
            message=message,
            priority=priority,
            category="trading",
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        await self.send_notification(notification)
    
    async def send_ml_notification(
        self, 
        title: str, 
        message: str, 
        priority: NotificationPriority = NotificationPriority.LOW,
        metadata: Dict[str, Any] = None
    ):
        """Send ML-related notification"""
        notification = Notification(
            title=title,
            message=message,
            priority=priority,
            category="ml",
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        await self.send_notification(notification)
    
    def _map_alert_priority(self, alert_level) -> NotificationPriority:
        """Map alert level to notification priority"""
        mapping = {
            "info": NotificationPriority.LOW,
            "warning": NotificationPriority.MEDIUM,
            "error": NotificationPriority.HIGH,
            "critical": NotificationPriority.CRITICAL
        }
        return mapping.get(alert_level.value, NotificationPriority.MEDIUM)
    
    def _is_rate_limited(self, key: str) -> bool:
        """Check if notification type is rate limited"""
        now = datetime.now()
        last_sent = self.rate_limits.get(key)
        
        if last_sent is None:
            self.rate_limits[key] = now
            return False
        
        # Rate limit: max 1 notification per 5 minutes for same category/priority
        time_diff = (now - last_sent).total_seconds()
        if time_diff < 300:  # 5 minutes
            return True
        
        self.rate_limits[key] = now
        return False
    
    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get notification history"""
        recent_notifications = self.notification_history[-limit:] if limit else self.notification_history
        
        return [
            {
                "title": notif.title,
                "message": notif.message,
                "priority": notif.priority.value,
                "category": notif.category,
                "timestamp": notif.timestamp.isoformat(),
                "metadata": notif.metadata
            }
            for notif in recent_notifications
        ]
    
    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all notification channels"""
        status = {}
        for channel_type, notifier in self.channels.items():
            status[channel_type.value] = {
                "enabled": True,
                "type": type(notifier).__name__,
                "configured": True
            }
        return status

# Global notification service instance
notification_service = NotificationService()