"""Notificações por e-mail. Sem SMTP configurado, apenas registra em log (decisão 8)."""
import logging
import smtplib

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, host, port, user, password, sender=None, smtp_factory=smtplib.SMTP):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender or user
        self._smtp_factory = smtp_factory

    @classmethod
    def from_settings(cls, settings):
        return cls(settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASSWORD)

    @property
    def enabled(self):
        return bool(self.host)

    def send_email(self, to, subject, body):
        if not self.enabled:
            logger.info("Notificação (SMTP desabilitado) para=%s assunto=%r", to, subject)
            return False
        try:
            with self._smtp_factory(self.host, self.port) as server:
                server.starttls()
                if self.user:
                    server.login(self.user, self.password)
                server.sendmail(self.sender, to, f"Subject: {subject}\n\n{body}")
            logger.info("Email enviado para=%s", to)
            return True
        except (smtplib.SMTPException, OSError):
            logger.warning("Falha ao enviar email para=%s", to, exc_info=True)
            return False

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}"
        )
        return self.send_email(user.email, subject, body)

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        return self.send_email(user.email, subject, body)
