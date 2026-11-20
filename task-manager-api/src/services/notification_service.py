"""Notificações por e-mail. Sem SMTP configurado, a notificação é só registrada no log."""
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, host, port, user, password, timeout):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._timeout = timeout

    @property
    def enabled(self):
        return bool(self._host and self._user and self._password)

    def send_email(self, to, subject, body):
        if not self.enabled:
            logger.info('Notificação para %s não enviada: SMTP não configurado', to)
            return
        message = EmailMessage()
        message['From'] = self._user
        message['To'] = to
        message['Subject'] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.send_message(message)
            logger.info('Email enviado para %s', to)
        except (smtplib.SMTPException, OSError):
            logger.exception('Falha ao enviar email para %s', to)

    def notify_task_assigned(self, user, task):
        logger.info('Notificando usuário %s sobre a task %s', user.id, task.id)
        subject = f'Nova task atribuída: {task.title}'
        body = (
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f'Prioridade: {task.priority}\nStatus: {task.status}'
        )
        self.send_email(user.email, subject, body)
