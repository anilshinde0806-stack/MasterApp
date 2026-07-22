/*
==============================================================================
MasterApp ERP

Object      : erp.notification_queue
Type        : Table
Description : Stores outgoing notifications for asynchronous processing
==============================================================================
*/

CREATE TABLE IF NOT EXISTS erp.notification_queue
(
    id                  BIGSERIAL PRIMARY KEY,

    module_code         VARCHAR(30) NOT NULL,

    notification_type   VARCHAR(20) NOT NULL,
        -- WHATSAPP
        -- EMAIL
        -- SMS
        -- PUSH

    recipient           VARCHAR(255) NOT NULL,

    subject             VARCHAR(255),

    message             TEXT NOT NULL,

    document_type       VARCHAR(30),

    document_id         BIGINT,

    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        -- PENDING
        -- PROCESSING
        -- SENT
        -- FAILED

    retry_count         INTEGER NOT NULL DEFAULT 0,

    error_message       TEXT,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    processed_at        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_status
ON erp.notification_queue(status);

CREATE INDEX IF NOT EXISTS idx_notification_module
ON erp.notification_queue(module_code);

DROP FUNCTION IF EXISTS erp.fn_enqueue_notification(
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    TEXT,
    VARCHAR,
    BIGINT
);

CREATE OR REPLACE FUNCTION erp.fn_enqueue_notification
(
    p_module_code       VARCHAR,
    p_notification_type VARCHAR,
    p_recipient         VARCHAR,
    p_subject           VARCHAR,
    p_message           TEXT,
    p_document_type     VARCHAR,
    p_document_id       BIGINT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS
$$
DECLARE
    v_queue_id BIGINT;
BEGIN

    INSERT INTO erp.notification_queue
    (
        module_code,
        notification_type,
        recipient,
        subject,
        message,
        document_type,
        document_id
    )
    VALUES
    (
        p_module_code,
        p_notification_type,
        p_recipient,
        p_subject,
        p_message,
        p_document_type,
        p_document_id
    )
    RETURNING id
    INTO v_queue_id;

    RETURN v_queue_id;

END;
$$;