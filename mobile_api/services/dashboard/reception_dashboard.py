class ReceptionDashboardService:
    """
    Dashboard for Reception
    """

    def __init__(self, user):
        self.user = user

    def get(self):
        return {
            "dashboard_type": "RECEPTION",
            "user": {},
            "notification_count": 0,
            "summaries": [],
            "performance": {},
            "actions": [],
            "recent_work": [],
        }