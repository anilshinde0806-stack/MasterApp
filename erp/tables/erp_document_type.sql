/*
=========================================================
Object      : erp.document_type
Module      : ERP
Description : Document Number Configuration
Version     : 1.0.0
=========================================================
*/

CREATE TABLE IF NOT EXISTS erp.document_type
(
    id                  BIGSERIAL PRIMARY KEY,

    module_code         VARCHAR(50) NOT NULL UNIQUE,

    module_name         VARCHAR(100) NOT NULL,

    prefix              VARCHAR(20) NOT NULL,

    format_pattern      VARCHAR(200) NOT NULL,

    number_padding      INTEGER NOT NULL DEFAULT 6,

    reset_policy        VARCHAR(20) NOT NULL DEFAULT 'YEAR',

    include_branch      BOOLEAN NOT NULL DEFAULT TRUE,

    include_year        BOOLEAN NOT NULL DEFAULT TRUE,

    active              BOOLEAN NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO erp.document_type
(
module_code,
module_name,
prefix,
format_pattern,
number_padding,
reset_policy
)

VALUES

(
'CLAIM',
'Claim',
'CLM',
'{PREFIX}-{BRANCH}-{YEAR}-{NUMBER}',
6,
'YEAR'
),

(
'JOBCARD',
'Job Card',
'JOB',
'{PREFIX}-{BRANCH}-{YEAR}-{NUMBER}',
6,
'YEAR'
),

(
'ESTIMATE',
'Estimate',
'EST',
'{PREFIX}-{BRANCH}-{YEAR}-{NUMBER}',
6,
'YEAR'
),

(
'INVOICE',
'Invoice',
'INV',
'{PREFIX}-{BRANCH}-{YEAR}-{NUMBER}',
6,
'YEAR'
),

(
'PART_ORDER',
'Part Order',
'PO',
'{PREFIX}-{BRANCH}-{YEAR}-{NUMBER}',
6,
'YEAR'
),

(
'PAYMENT',
'Payment',
'PAY',
'{PREFIX}-{BRANCH}-{YEAR}-{NUMBER}',
6,
'YEAR'
)

ON CONFLICT (module_code)
DO NOTHING;