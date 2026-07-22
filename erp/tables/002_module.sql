/*
==========================================================
MasterApp ERP

Object      : erp.module
Description : ERP Modules
Version     : 1.0.0
==========================================================
*/

CREATE TABLE IF NOT EXISTS erp.module
(
    id              BIGSERIAL PRIMARY KEY,

    module_code     VARCHAR(30) NOT NULL UNIQUE,

    module_name     VARCHAR(100) NOT NULL,

    description     TEXT,

    active          BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),

    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
INSERT INTO erp.module
(
module_code,
module_name,
description
)

VALUES

('CLAIM','Claims','Insurance Claim Management'),

('JOBCARD','Job Cards','Workshop Job Card'),

('ESTIMATE','Estimate','Estimate Module'),

('INVOICE','Invoice','Customer Invoice'),

('PARTS','Parts','Inventory Parts'),

('PURCHASE','Purchase','Purchase Orders'),

('DELIVERY','Delivery','Vehicle Delivery'),

('QC','Quality Control','Quality Inspection'),

('CRM','CRM','Customer Relationship'),

('HR','Human Resource','Employees'),

('REPORT','Reports','Reporting'),

('ADMIN','Administration','ERP Administration')

ON CONFLICT (module_code)
DO NOTHING;