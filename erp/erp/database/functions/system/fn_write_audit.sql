DROP FUNCTION IF EXISTS erp.fn_write_audit(
    VARCHAR,
    VARCHAR,
    BIGINT,
    VARCHAR,
    JSONB,
    JSONB,
    INTEGER,
    INTEGER,
    TEXT
);

CREATE OR REPLACE FUNCTION erp.fn_write_audit
(
    p_module_code   VARCHAR,
    p_document_type VARCHAR,
    p_document_id   BIGINT,
    p_action        VARCHAR,
    p_old_data      JSONB,
    p_new_data      JSONB,
    p_user_id       INTEGER,
    p_branch_id     INTEGER,
    p_remarks       TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS
$$
BEGIN

    INSERT INTO erp.audit_log
    (
        module_code,
        document_type,
        document_id,
        action,
        old_data,
        new_data,
        user_id,
        branch_id,
        remarks
    )
    VALUES
    (
        p_module_code,
        p_document_type,
        p_document_id,
        p_action,
        p_old_data,
        p_new_data,
        p_user_id,
        p_branch_id,
        p_remarks
    );

END;
$$;