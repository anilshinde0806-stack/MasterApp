from rest_framework import serializers


class DashboardUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField()
    employee_type = serializers.CharField()
    designation = serializers.CharField()
    department = serializers.CharField(required=False, allow_blank=True)
    branch = serializers.CharField(required=False, allow_blank=True)
    profile_image = serializers.CharField(
        allow_null=True,
        required=False,
    )


class DashboardSummarySerializer(serializers.Serializer):
    title = serializers.CharField()
    value = serializers.IntegerField()
    type = serializers.CharField()
    color = serializers.CharField(required=False)
    icon = serializers.CharField(required=False)


class DashboardPerformanceSerializer(serializers.Serializer):
    total_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    pending_jobs = serializers.IntegerField()
    running_jobs = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    average_tat = serializers.CharField()


class DashboardActionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    icon = serializers.CharField()
    route = serializers.CharField()
    color = serializers.CharField()


class PendingActionCategorySerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    count = serializers.IntegerField()
    icon = serializers.CharField()
    color = serializers.CharField()
    desktop_url = serializers.CharField()
    route = serializers.CharField()


class PendingActionItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField()
    claim_id = serializers.IntegerField()
    claim_no = serializers.CharField()
    job_id = serializers.IntegerField(allow_null=True)
    job_no = serializers.CharField(allow_blank=True)
    vehicle_no = serializers.CharField(allow_blank=True)
    customer_name = serializers.CharField(allow_blank=True)
    stage = serializers.CharField()
    age_days = serializers.IntegerField()
    priority = serializers.CharField()
    desktop_url = serializers.CharField()
    route = serializers.CharField()


class PendingActionsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    categories = PendingActionCategorySerializer(many=True)
    items = PendingActionItemSerializer(many=True)


class RecentWorkSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    progress_id = serializers.IntegerField(required=False)
    job_no = serializers.CharField()
    claim_no = serializers.CharField()
    vehicle_no = serializers.CharField()
    customer_name = serializers.CharField()
    advisor = serializers.CharField()
    technician = serializers.CharField(required=False)
    insurance_company = serializers.CharField(required=False)
    status = serializers.CharField()
    priority = serializers.CharField(required=False)
    progress = serializers.FloatField(required=False, default=0)
    photo_count = serializers.IntegerField(required=False, default=0)
    remarks_added = serializers.BooleanField(required=False, default=False)
    updated_at = serializers.CharField(required=False, allow_blank=True)



class DashboardPipelineSerializer(serializers.Serializer):
    stage = serializers.IntegerField(required=False)
    title = serializers.CharField()
    count = serializers.IntegerField()
    icon = serializers.CharField(required=False)
    color = serializers.CharField(required=False)


class FollowupSerializer:
    title = serializers.CharField()
    subtitle = serializers.CharField()
    count = serializers.IntegerField()
    icon = serializers.CharField()
    color = serializers.CharField()
    route = serializers.CharField()


class DashboardFinancialSerializer:
    estimate = serializers.DecimalField(max_digits=14, decimal_places=2)
    approved = serializers.DecimalField(max_digits=14, decimal_places=2)
    invoice = serializers.DecimalField(max_digits=14, decimal_places=2)
    collection = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)

    average_job_value = serializers.DecimalField(max_digits=14, decimal_places=2)

    gross_profit = serializers.DecimalField(max_digits=14, decimal_places=2)

    net_profit = serializers.DecimalField(max_digits=14, decimal_places=2)


class TopAdvisorSerializer:
    id = serializers.IntegerField()

    name = serializers.CharField()

    completed_jobs = serializers.IntegerField()

    revenue = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    average_tat = serializers.FloatField()

    rating = serializers.FloatField()


class TopTechnicianSerializer:
    id = serializers.IntegerField()

    name = serializers.CharField()

    department = serializers.CharField()

    completed_jobs = serializers.IntegerField()

    efficiency = serializers.FloatField()


class BranchPerformanceSerializer:
    id = serializers.IntegerField()

    name = serializers.CharField()

    jobs = serializers.IntegerField()

    revenue = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    tat = serializers.FloatField()


class NotificationSummarySerializer:
    count = serializers.IntegerField()
    unread = serializers.IntegerField()





class DashboardSerializer(serializers.Serializer):

    dashboard_type = serializers.CharField()

    user = DashboardUserSerializer()

    notification_count = serializers.IntegerField()

    summaries = DashboardSummarySerializer(many=True)

    performance = DashboardPerformanceSerializer()

    financial = serializers.DictField(required=False)

    top_advisors = serializers.ListField(required=False)

    top_technicians = serializers.ListField(required=False)

    branch_performance = serializers.ListField(required=False)

    revenue = serializers.ListField(required=False)

    actions = DashboardActionSerializer(many=True)

    recent_work = RecentWorkSerializer(many=True)

    pipeline = DashboardPipelineSerializer(many=True)

    pending_actions = PendingActionsSerializer(required=False)



