/*
==============================================================================
MasterApp ERP

Object      : erp.audit_log
Type        : Table
Description : Stores audit trail for all ERP modules
==============================================================================
*/

CREATE TABLE IF NOT EXISTS erp.audit_log
(
    id              BIGSERIAL PRIMARY KEY,

    module_code     VARCHAR(30) NOT NULL,
    document_type   VARCHAR(30),
    document_id     BIGINT,

    action          VARCHAR(30) NOT NULL,

    old_data        JSONB,
    new_data        JSONB,

    user_id         INTEGER,
    branch_id       INTEGER,

    remarks         TEXT,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_module
ON erp.audit_log(module_code);

CREATE INDEX IF NOT EXISTS idx_audit_document
ON erp.audit_log(document_id);

CREATE INDEX IF NOT EXISTS idx_audit_created
ON erp.audit_log(created_at);