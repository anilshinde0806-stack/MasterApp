/*
==============================================================================
MasterApp ERP

Object      : erp.fn_generate_document_no
Type        : Function
Description : Generates unique document number

Example     : CLM-HO-2026-000001

Version     : 1.0.0
==============================================================================
*/

DROP FUNCTION IF EXISTS erp.fn_generate_document_no(VARCHAR, INTEGER);

CREATE OR REPLACE FUNCTION erp.fn_generate_document_no
(
    p_module_code VARCHAR,
    p_branch_id   INTEGER
)
RETURNS VARCHAR
LANGUAGE plpgsql
AS
$$
DECLARE
    v_document_type_id INTEGER;
    v_prefix           VARCHAR;
    v_padding          INTEGER;
    v_include_branch   BOOLEAN;
    v_include_year     BOOLEAN;

    v_branch_code      VARCHAR;
    v_year             INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);

    v_last_number      INTEGER;
    v_document_no      VARCHAR;
BEGIN

    --------------------------------------------------------------------------
    -- Get Document Configuration
    --------------------------------------------------------------------------

    SELECT
        id,
        prefix,
        number_padding,
        include_branch,
        include_year
    INTO
        v_document_type_id,
        v_prefix,
        v_padding,
        v_include_branch,
        v_include_year
    FROM erp.document_type
    WHERE module_code = p_module_code
      AND active = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Document type "%" not configured.', p_module_code;
    END IF;

    --------------------------------------------------------------------------
    -- Get Branch Code
    --------------------------------------------------------------------------

    v_branch_code := erp.fn_get_branch_code(p_branch_id);

    --------------------------------------------------------------------------
    -- Create sequence row if missing
    --------------------------------------------------------------------------

    INSERT INTO erp.document_sequence
    (
        document_type_id,
        branch_id,
        sequence_year,
        last_number
    )
    SELECT
        v_document_type_id,
        p_branch_id,
        v_year,
        0
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM erp.document_sequence
        WHERE document_type_id = v_document_type_id
          AND branch_id = p_branch_id
          AND sequence_year = v_year
    );

    --------------------------------------------------------------------------
    -- Lock sequence row
    --------------------------------------------------------------------------

    SELECT last_number
    INTO v_last_number
    FROM erp.document_sequence
    WHERE document_type_id = v_document_type_id
      AND branch_id = p_branch_id
      AND sequence_year = v_year
    FOR UPDATE;

    --------------------------------------------------------------------------
    -- Increment
    --------------------------------------------------------------------------

    v_last_number := v_last_number + 1;

    UPDATE erp.document_sequence
       SET last_number = v_last_number,
           updated_at = NOW()
     WHERE document_type_id = v_document_type_id
       AND branch_id = p_branch_id
       AND sequence_year = v_year;

    --------------------------------------------------------------------------
    -- Format
    --------------------------------------------------------------------------

    v_document_no := v_prefix;

    IF v_include_branch THEN
        v_document_no := v_document_no || '-' || v_branch_code;
    END IF;

    IF v_include_year THEN
        v_document_no := v_document_no || '-' || v_year;
    END IF;

    v_document_no :=
        v_document_no
        || '-'
        || LPAD(v_last_number::TEXT, v_padding, '0');

    RETURN v_document_no;

END;
$$;