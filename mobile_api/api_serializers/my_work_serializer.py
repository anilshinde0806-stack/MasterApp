from rest_framework import serializers

class MyWorkSerializer(serializers.Serializer):

    id = serializers.IntegerField()

    job_no = serializers.CharField()

    claim_no = serializers.CharField()

    ic_claim_no = serializers.CharField()

    vehicle_no = serializers.CharField()

    vehicle_model = serializers.CharField()

    customer_name = serializers.CharField()

    advisor = serializers.CharField()

    technician = serializers.CharField()

    work_type = serializers.CharField()

    status = serializers.CharField()

    priority = serializers.CharField()

    progress = serializers.IntegerField()

    assigned_at = serializers.DateTimeField()

    started_at = serializers.DateTimeField(allow_null=True)

    completed_at = serializers.DateTimeField(allow_null=True)

    remarks = serializers.CharField()

    before_photos = serializers.ListField()

    after_photos = serializers.ListField()