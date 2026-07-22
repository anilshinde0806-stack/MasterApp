import traceback

from rest_framework import status
from rest_framework.exceptions import ValidationError


class BaseService:

    def __init__(self, user):
        self.user = user

    def success(self, data=None, message="Success"):
        return {
            "success": True,
            "message": message,
            "data": data,
        }

    def error(self, message, errors=None):
        return {
            "success": False,
            "message": message,
            "errors": errors or {},
        }

    def execute(self, callback):
        try:
            return {
                "data": callback(),
                "status": status.HTTP_200_OK,
            }

        except ValidationError as exc:
            traceback.print_exc()  # <-- add this
            return {
                "data": exc.detail,
                "status": status.HTTP_400_BAD_REQUEST,
            }

        except Exception as exc:
            return {
                "data": self.error(
                    "Something went wrong.",
                    {"detail": str(exc)},
                ),
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    def save(self, data, pk=None):
        return self.execute(
            lambda: self.process(data, pk)
        )

    def process(self, data, pk=None):
        raise NotImplementedError
