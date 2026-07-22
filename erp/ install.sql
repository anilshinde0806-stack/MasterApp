/*
=========================================================
MasterApp ERP Database Installer
Version : 1.0.0
Database: PostgreSQL
=========================================================
*/

-- Create ERP schema
\i schema/001_create_erp_schema.sql

-- Functions
-- \i functions/fn_generate_claim_no.sql
-- \i functions/fn_claim_stage.sql

-- Views
-- \i views/vw_claim_dashboard.sql

-- Procedures
-- \i procedures/sp_save_claim.sql

-- Triggers
-- \i triggers/trg_claim_history.sql