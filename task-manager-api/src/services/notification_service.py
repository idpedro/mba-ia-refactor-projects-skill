import logging
import smtplib

from src.database import utcnow

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 10


class NotificationService:
    """Uma instância criada em create_app() e injetada; o histórico vive nessa instância."""

    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.notifications = []

    def send_email(self, to, subject, body):
        if not self.host:
            logger.info("SMTP não configurado; email para %s não enviado: %s", to, subject)
            return False
        try:
            with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.starttls()
                if self.user:
                    server.login(self.user, self.password)
                server.sendmail(self.user, to, f"Subject: {subject}\n\n{body}")
            logger.info("Email enviado para %s", to)
            return True
        except (smtplib.SMTPException, OSError):
            logger.exception("Erro ao enviar email para %s", to)
            return False

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}"
        )
        self.send_email(user.email, subject, body)
        self.notifications.append(
            {"type": "task_assigned", "user_id": user.id, "task_id": task.id, "timestamp": utcnow()}
        )

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        self.send_email(user.email, subject, body)

    def get_notifications(self, user_id):
        return [notification for notification in self.notifications if notification["user_id"] == user_id]
