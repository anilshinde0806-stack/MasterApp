from django.db import connection


class BaseERPService:

    @staticmethod
    def execute_scalar(query, params):
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else None

    @staticmethod
    def execute(query, params):
        with connection.cursor() as cursor:
            cursor.execute(query, params)