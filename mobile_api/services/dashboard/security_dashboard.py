class SecurityDashboardService:
    """
    Dashboard for Gate Security
    """

    def __init__(self, user):
        self.user = user

    def get(self):
        return {
            "dashboard_type": "SECURITY",
            "user": {},
            "notification_count": 0,
            "summaries": [],
            "performance": {},
            "actions": [],
            "recent_work": [],
        }