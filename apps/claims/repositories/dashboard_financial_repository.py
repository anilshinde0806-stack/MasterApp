"""PostgreSQL-backed dashboard financial read model."""

from decimal import Decimal

from django.db import connection


class DashboardFinancialRepository:
    FUNCTION_NAME = "bodyshop_dashboard_financial"

    @classmethod
    def is_available(cls):
        if connection.vendor != "postgresql":
            return False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_regprocedure(%s) IS NOT NULL",
                [f"{cls.FUNCTION_NAME}(bigint[],date,date)"],
            )
            return cursor.fetchone()[0]

    @classmethod
    def get(cls, *, claim_ids, start_date=None, end_date=None):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {cls.FUNCTION_NAME}(%s, %s, %s)",
                [list(claim_ids), start_date, end_date],
            )
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
        return dict(zip(columns, row)) if row else {}

    @staticmethod
    def decimal(value):
        return value if isinstance(value, Decimal) else Decimal(value or 0)
