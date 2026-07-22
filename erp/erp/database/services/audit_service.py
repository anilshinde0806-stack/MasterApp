from django.db import connection
from psycopg.types.json import Json


class AuditService:
    """
    ERP Audit Service
    """

    @staticmethod
    def write(
        module_code,
        document_type,
        document_id,
        action,
        old_data=None,
        new_data=None,
        user_id=None,
        branch_id=None,
        remarks=None,
    ):

        with connection.cursor() as cursor:
            import json

            cursor.execute(
                """
                SELECT erp.fn_write_audit(
                    %s::varchar,
                    %s::varchar,
                    %s::bigint,
                    %s::varchar,
                    %s::jsonb,
                    %s::jsonb,
                    %s::integer,
                    %s::integer,
                    %s::text
                )
                """,
                (
                    module_code,
                    document_type,
                    document_id,
                    action,
                    json.dumps(old_data or {}),
                    json.dumps(new_data or {}),
                    user_id,
                    branch_id,
                    remarks,
                ),
            )