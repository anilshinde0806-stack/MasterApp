/*
=========================================================
Object      : erp.document_sequence
Module      : ERP
Description : Stores Current Running Number
Version     : 1.0.0
=========================================================
*/

CREATE TABLE IF NOT EXISTS erp.document_sequence
(
    id                  BIGSERIAL PRIMARY KEY,

    document_type_id    BIGINT NOT NULL
        REFERENCES erp.document_type(id),

    company_id          INTEGER DEFAULT 1,

    branch_id           INTEGER NOT NULL,

    sequence_period     VARCHAR(20) NOT NULL,

    current_value       BIGINT NOT NULL DEFAULT 0,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_document_sequence
    UNIQUE
    (
        company_id,
        document_type_id,
        branch_id,
        sequence_period
    )
);
CREATE INDEX IF NOT EXISTS idx_document_sequence_lookup
ON erp.document_sequence
(
    company_id,
    document_type_id,
    branch_id,
    sequence_period
);