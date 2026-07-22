/*
==============================================================================
MasterApp ERP

Object      : erp.fn_get_setting
Type        : Function
Description : Returns the value of an ERP setting
Author      : MasterApp
Version     : 1.0.0
Created     : 18-Jul-2026
==============================================================================
*/

DROP FUNCTION IF EXISTS erp.fn_get_setting(VARCHAR);

CREATE OR REPLACE FUNCTION erp.fn_get_setting
(
    p_setting_key VARCHAR
)
RETURNS TEXT
LANGUAGE plpgsql
STABLE
AS
$$
DECLARE
    v_setting_value TEXT;
BEGIN

    SELECT s.setting_value
      INTO v_setting_value
      FROM erp.settings s
     WHERE s.setting_key = p_setting_key
       AND s.active = TRUE
     LIMIT 1;

    RETURN v_setting_value;

END;
$$;

COMMENT ON FUNCTION erp.fn_get_setting(VARCHAR)
IS 'Returns ERP setting value.';