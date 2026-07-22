class DefaultDashboardService:
    """
    Default dashboard for users without a specific role
    """

    def __init__(self, user):
        self.user = user

    def get(self):
        return {
            "dashboard_type": "DEFAULT",
            "user": {},
            "notification_count": 0,
            "summaries": [],
            "performance": {},
            "actions": [],
            "recent_work": [],
        }