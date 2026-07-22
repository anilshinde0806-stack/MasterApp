from django.db import connection


class NotificationService:
    """
    ERP Notification Queue
    """

    @staticmethod
    def enqueue(
        module_code,
        notification_type,
        recipient,
        subject,
        message,
        document_type,
        document_id,
    ):

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT erp.fn_enqueue_notification(
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                [
                    module_code,
                    notification_type,
                    recipient,
                    subject,
                    message,
                    document_type,
                    document_id,
                ],
            )

            row = cursor.fetchone()

        return row[0] if row else None