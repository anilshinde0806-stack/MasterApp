from django.db import connection

from erp.erp.database.services.base_erp_service import BaseERPService


class DocumentService(BaseERPService):

    @staticmethod
    def generate(module_code, branch_id):
        return DocumentService.execute_scalar(
            """
            SELECT erp.fn_generate_document_no(%s,%s)
            """,
            [module_code, branch_id],
        )

            