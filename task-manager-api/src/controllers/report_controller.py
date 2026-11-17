from src.errors import NotFoundError


class ReportController:
    def __init__(self, users, report_service):
        self.users = users
        self.reports = report_service

    def summary(self):
        return self.reports.summary()

    def user_report(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError('Usuário não encontrado')
        return self.reports.user_report(user)
