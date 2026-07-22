/*
==========================================================
MasterApp ERP

Object      : erp.settings
Description : ERP Configuration
Version     : 1.0.0
==========================================================
*/

CREATE TABLE IF NOT EXISTS erp.settings
(
    id                  BIGSERIAL PRIMARY KEY,

    setting_key         VARCHAR(100) NOT NULL UNIQUE,

    setting_value       TEXT,

    description         TEXT,

    data_type           VARCHAR(20) NOT NULL DEFAULT 'STRING',

    category            VARCHAR(50) NOT NULL DEFAULT 'GENERAL',

    is_editable         BOOLEAN NOT NULL DEFAULT TRUE,

    active              BOOLEAN NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_setting_type
    CHECK
    (
        data_type IN
        (
            'STRING',
            'INTEGER',
            'BOOLEAN',
            'DECIMAL',
            'DATE',
            'JSON'
        )
    )
);
INSERT INTO erp.settings
(
setting_key,
setting_value,
description,
data_type,
category
)

VALUES

(
'COMPANY_NAME',
'Master Body Shop',
'Company Name',
'STRING',
'GENERAL'
),

(
'DEFAULT_CURRENCY',
'INR',
'Currency',
'STRING',
'GENERAL'
),

(
'WHATSAPP_ENABLED',
'TRUE',
'Enable WhatsApp',
'BOOLEAN',
'NOTIFICATION'
),

(
'EMAIL_ENABLED',
'TRUE',
'Enable Email',
'BOOLEAN',
'NOTIFICATION'
),

(
'SMS_ENABLED',
'FALSE',
'Enable SMS',
'BOOLEAN',
'NOTIFICATION'
),

(
'DEFAULT_PAGE_SIZE',
'25',
'Default Page Size',
'INTEGER',
'SYSTEM'
),

(
'DOCUMENT_PADDING',
'6',
'Default Document Padding',
'INTEGER',
'DOCUMENT'
),

(
'CURRENT_FINANCIAL_YEAR',
'2026-27',
'Current Financial Year',
'STRING',
'FINANCE'
)

ON CONFLICT (setting_key)
DO NOTHING;