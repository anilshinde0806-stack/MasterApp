from django.db import migrations


FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION bodyshop_dashboard_metrics(
    p_claim_ids bigint[], p_period_claim_ids bigint[], p_jobcard_ids bigint[],
    p_start_date date, p_end_date date
)
RETURNS TABLE (
    total_claims bigint, pending_claims bigint, closed_claims bigint,
    work_allocation_pending bigint, repair_in_progress bigint,
    stage_counts jsonb, advisor_counts jsonb, total_estimate_value numeric
)
LANGUAGE sql STABLE AS $function$
WITH scoped AS (
    SELECT * FROM core_claim WHERE id = ANY(COALESCE(p_claim_ids, ARRAY[]::bigint[]))
), period_claims AS (
    SELECT * FROM core_claim WHERE id = ANY(COALESCE(p_period_claim_ids, ARRAY[]::bigint[]))
), open_values AS (
    SELECT
        COUNT(*) AS pending,
        COUNT(*) FILTER (WHERE claim_stage = 7) AS allocation,
        COUNT(*) FILTER (WHERE claim_stage = 8) AS repair
    FROM scoped
    WHERE created_at::date <= p_end_date
      AND claim_stage <> 14
      AND LOWER(COALESCE(status, '')) NOT IN ('closed', 'cancelled')
), closed_values AS (
    SELECT COUNT(*) AS total FROM scoped
    WHERE (claim_stage = 14 OR LOWER(COALESCE(status, '')) = 'closed')
      AND (
        delivery_datetime::date BETWEEN p_start_date AND p_end_date
        OR (delivery_datetime IS NULL AND updated_at::date BETWEEN p_start_date AND p_end_date)
      )
), stages AS (
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object('claim_stage', claim_stage, 'total', total)
        ORDER BY claim_stage
    ), '[]'::jsonb) AS rows
    FROM (SELECT claim_stage, COUNT(*) AS total FROM period_claims GROUP BY claim_stage) s
), advisors AS (
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'employee__name', name,
            'employee__branch__code', branch_code,
            'employee__branch__name', branch_name,
            'total', total
        ) ORDER BY total DESC
    ), '[]'::jsonb) AS rows
    FROM (
        SELECT e.name, b.code AS branch_code, b.name AS branch_name, COUNT(*) AS total
        FROM period_claims c
        LEFT JOIN core_employee e ON e.id = c.employee_id
        LEFT JOIN core_branch b ON b.id = e.branch_id
        GROUP BY e.name, b.code, b.name ORDER BY total DESC LIMIT 10
    ) a
), estimates AS (
    SELECT COALESCE(SUM(grand_total), 0) AS total
    FROM core_jobcard WHERE id = ANY(COALESCE(p_jobcard_ids, ARRAY[]::bigint[]))
)
SELECT
    o.pending + c.total, o.pending, c.total, o.allocation, o.repair,
    s.rows, a.rows, e.total
FROM open_values o CROSS JOIN closed_values c CROSS JOIN stages s
CROSS JOIN advisors a CROSS JOIN estimates e;
$function$;
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0094_dashboard_financial_function")]
    operations = [migrations.RunSQL(
        FUNCTION_SQL,
        "DROP FUNCTION IF EXISTS bodyshop_dashboard_metrics(bigint[], bigint[], bigint[], date, date);",
    )]
