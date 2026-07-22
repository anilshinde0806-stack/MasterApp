from django.db import migrations


FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION bodyshop_dashboard_financial(
    p_claim_ids bigint[],
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL
)
RETURNS TABLE (
    estimate numeric,
    approved numeric,
    approved_parts numeric,
    approved_labour numeric,
    liability numeric,
    invoice numeric,
    parts numeric,
    labour numeric,
    collection numeric,
    outstanding numeric,
    average_job_value numeric
)
LANGUAGE sql
STABLE
AS $function$
WITH scoped_claims AS (
    SELECT c.*
    FROM core_claim c
    WHERE c.id = ANY(COALESCE(p_claim_ids, ARRAY[]::bigint[]))
),
estimate_values AS (
    SELECT COALESCE(SUM(
        CASE WHEN COALESCE(c.estimated_amount, 0) > 0
             THEN c.estimated_amount
             ELSE COALESCE(j.grand_total, 0) END
    ), 0) AS total
    FROM scoped_claims c
    LEFT JOIN core_jobcard j ON j.claim_id = c.id
    WHERE (p_start_date IS NULL OR c.created_at::date >= p_start_date)
      AND (p_end_date IS NULL OR c.created_at::date <= p_end_date)
),
direct_approval AS (
    SELECT COALESCE(SUM(
        CASE WHEN COALESCE(c.approved_amount, 0) > 0 THEN c.approved_amount
             WHEN COALESCE(c.liability_do_amount, 0) > 0 THEN c.liability_do_amount
             ELSE 0 END
    ), 0) AS total
    FROM scoped_claims c
    WHERE (p_start_date IS NULL OR c.insurance_approval_date::date >= p_start_date)
      AND (p_end_date IS NULL OR c.insurance_approval_date::date <= p_end_date)
),
fallback_claims AS (
    SELECT DISTINCT c.id
    FROM scoped_claims c
    JOIN core_jobcard j ON j.claim_id = c.id
    WHERE COALESCE(c.approved_amount, 0) <= 0
      AND COALESCE(c.liability_do_amount, 0) <= 0
      AND (p_start_date IS NULL OR j.created_at::date >= p_start_date)
      AND (p_end_date IS NULL OR j.created_at::date <= p_end_date)
),
assessment_parts AS (
    SELECT COALESCE(SUM(p.revised_amount), 0) AS total
    FROM core_jobcardassessmentpart p
    JOIN core_jobcard j ON j.id = p.job_id
    JOIN fallback_claims f ON f.id = j.claim_id
    WHERE p.decision IN ('New', 'Repair', 'KO')
),
assessment_labour AS (
    SELECT COALESCE(SUM(l.revised_amount), 0) AS total
    FROM core_jobcardassessmentlabour l
    JOIN core_jobcard j ON j.id = l.job_id
    JOIN fallback_claims f ON f.id = j.claim_id
    WHERE l.decision = 'Approved'
),
liability_values AS (
    SELECT COALESCE(SUM(c.liability_do_amount), 0) AS total
    FROM scoped_claims c
    WHERE (p_start_date IS NULL OR c.liability_received_at::date >= p_start_date)
      AND (p_end_date IS NULL OR c.liability_received_at::date <= p_end_date)
),
invoice_values AS (
    SELECT
        COALESCE(SUM(c.invoice_amount), 0) AS invoice,
        COALESCE(SUM(c.invoice_parts_amount), 0) AS parts,
        COALESCE(SUM(c.invoice_labour_amount), 0) AS labour,
        COALESCE(SUM(CASE WHEN COALESCE(c.payment_mode, '') <> ''
                          THEN c.invoice_amount ELSE 0 END), 0) AS collection,
        COUNT(*) FILTER (WHERE COALESCE(c.invoice_amount, 0) > 0) AS invoice_count
    FROM scoped_claims c
    WHERE (p_start_date IS NULL OR c.invoice_datetime::date >= p_start_date)
      AND (p_end_date IS NULL OR c.invoice_datetime::date <= p_end_date)
)
SELECT
    e.total,
    d.total + ap.total + al.total,
    ap.total,
    al.total,
    lv.total,
    iv.invoice,
    iv.parts,
    iv.labour,
    iv.collection,
    GREATEST(iv.invoice - iv.collection, 0),
    CASE WHEN iv.invoice_count > 0 THEN iv.invoice / iv.invoice_count ELSE 0 END
FROM estimate_values e
CROSS JOIN direct_approval d
CROSS JOIN assessment_parts ap
CROSS JOIN assessment_labour al
CROSS JOIN liability_values lv
CROSS JOIN invoice_values iv;
$function$;
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0093_rename_core_gatein_registr_6813b3_idx_core_gatein_registr_b74fa9_idx_and_more")]

    operations = [
        migrations.RunSQL(
            sql=FUNCTION_SQL,
            reverse_sql="DROP FUNCTION IF EXISTS bodyshop_dashboard_financial(bigint[], date, date);",
        ),
    ]
