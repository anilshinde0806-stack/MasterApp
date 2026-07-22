from django.db import migrations


FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION bodyshop_dashboard_kpis(
    p_claim_ids bigint[], p_jobcard_ids bigint[]
)
RETURNS TABLE (
    open_claims bigint, open_jobcards bigint, workshop bigint,
    insurance bigint, survey bigint, delivery bigint, pipeline_counts jsonb
)
LANGUAGE sql STABLE AS $function$
WITH claims AS (
    SELECT * FROM core_claim
    WHERE id = ANY(COALESCE(p_claim_ids, ARRAY[]::bigint[]))
), jobs AS (
    SELECT * FROM core_jobcard
    WHERE id = ANY(COALESCE(p_jobcard_ids, ARRAY[]::bigint[]))
), claim_values AS (
    SELECT
        COUNT(*) FILTER (WHERE status = 'Open') AS open_claims,
        COUNT(*) FILTER (WHERE status = 'Open' AND claim_stage = 6) AS insurance,
        COUNT(*) FILTER (WHERE status = 'Open' AND claim_stage = 5) AS survey
    FROM claims
), job_values AS (
    SELECT
        COUNT(*) FILTER (WHERE repair_status = 'Open') AS open_jobs,
        COUNT(*) FILTER (WHERE ready_for_delivery = TRUE) AS delivery
    FROM jobs
), pipeline AS (
    SELECT COALESCE(jsonb_object_agg(claim_stage::text, total), '{}'::jsonb) AS counts
    FROM (
        SELECT claim_stage, COUNT(*) AS total
        FROM claims WHERE status = 'Open' GROUP BY claim_stage
    ) grouped
)
SELECT c.open_claims, j.open_jobs, j.open_jobs, c.insurance, c.survey,
       j.delivery, p.counts
FROM claim_values c CROSS JOIN job_values j CROSS JOIN pipeline p;
$function$;
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0095_dashboard_metrics_function")]
    operations = [migrations.RunSQL(
        FUNCTION_SQL,
        "DROP FUNCTION IF EXISTS bodyshop_dashboard_kpis(bigint[], bigint[]);",
    )]
