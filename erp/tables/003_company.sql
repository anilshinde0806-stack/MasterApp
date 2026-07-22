/*
=========================================================
Object      : erp.company
Module      : ERP
Description : Company Master
Version     : 1.0.0
=========================================================
*/

CREATE TABLE IF NOT EXISTS erp.company
(
    id                  BIGSERIAL PRIMARY KEY,

    company_code        VARCHAR(20) UNIQUE NOT NULL,

    company_name        VARCHAR(200) NOT NULL,

    short_name          VARCHAR(50),

    gst_no              VARCHAR(30),

    pan_no              VARCHAR(20),

    cin_no              VARCHAR(30),

    phone               VARCHAR(30),

    email               VARCHAR(100),

    website             VARCHAR(100),

    active              BOOLEAN NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);