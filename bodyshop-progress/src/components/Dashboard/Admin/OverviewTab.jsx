import React from "react";

import "./OverviewTab.css";

import {
  FileText,
  ClipboardList,
  Car,
  ShieldCheck,
  Camera,
  Truck,
  Briefcase,
  CheckCircle2,
  Activity,
  Clock3,
  BarChart3,
  Timer,
  Inbox,
  AlertTriangle,
  CarFront,
  ClipboardCheck,
  Gauge,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Label,
} from "recharts";

function ClaimsTooltip({ active, payload }) {

  if (!active || !payload || !payload.length) {
    return null;
  }

  const item = payload[0]?.payload;

  if (!item) {
    return null;
  }

  return (

    <div className="claims-tooltip">

      <div className="claims-tooltip-title">

        <span
          className="claims-tooltip-dot"
          style={{
            backgroundColor: item.color
          }}
        />

        <strong>
          {item.title}
        </strong>

      </div>


      <div className="claims-tooltip-row">

        <span>Claims</span>

        <b>
          {item.count}
        </b>

      </div>


      <div className="claims-tooltip-row">

        <span>Percentage</span>

        <b>
          {item.percentage}%
        </b>

      </div>

    </div>

  );

}

/* =====================================================
   SUMMARY ICONS
===================================================== */

const summaryIcons = {
  claims: FileText,
  jobcards: ClipboardList,
  workshop: Car,
  insurance: ShieldCheck,
  survey: Camera,
  delivery: Truck,
};


/* =====================================================
   WORKSHOP PERFORMANCE ICONS
===================================================== */

const performanceIcons = {
  total_jobs: Briefcase,
  total_vehicles: CarFront,
  completed_jobs: CheckCircle2,
  running_jobs: Activity,
  pending_jobs: Clock3,
  completion_percentage: BarChart3,
  average_tat: Timer,
  ready_for_delivery: ClipboardCheck,
};
/* =====================================================
   TILE NAVIGATION
===================================================== */

const summaryTabMapping = {

  claims: "financial",

  jobcards: "workshop",

  workshop: "workshop",

  insurance: "insurance",

  survey: "performance",

  delivery: "workshop",

};
const performanceTabMapping = {

  total_jobs: "workshop",

  total_vehicles: "workshop",

  pending_jobs: "workshop",

  running_jobs: "workshop",

  completed_jobs: "workshop",

  ready_for_delivery: "workshop",

  completion_percentage: "workshop",

  average_tat: "workshop",

};
const attentionTabMapping = {

  overdue_jobs: "alerts",

  qc_pending: "workshop",

  road_test_pending: "workshop",

  washing_pending: "workshop",

};

/* =====================================================
   CLAIM STAGES
===================================================== */

const claimStageConfig = [

  {
    key: "1",
    title: "Claim Created",
    color: "#2563EB",
  },

  {
    key: "2",
    title: "Advisor Assigned",
    color: "#7C3AED",
  },

  {
    key: "3",
    title: "Estimate Created",
    color: "#0891B2",
  },

  {
    key: "4",
    title: "Claim Intimation",
    color: "#F59E0B",
  },

  {
    key: "5",
    title: "Survey Done",
    color: "#06B6D4",
  },

  {
    key: "6",
    title: "Insurance Approval",
    color: "#16A34A",
  },

  {
    key: "7",
    title: "Work Allocation Pending",
    color: "#F97316",
  },

  {
    key: "8",
    title: "Repair Work In Progress",
    color: "#8B5CF6",
  },

  {
    key: "9",
    title: "Work Completed",
    color: "#22C55E",
  },

];
/* =====================================================
   SKELETON TILE
===================================================== */

function SkeletonTile() {

  return (

    <div
      className="overview-tile skeleton-tile"
      aria-hidden="true"
    >

      <div className="tile-icon skeleton-block" />

      <div className="tile-content">

        <span className="tile-label skeleton-block skeleton-line-short" />

        <strong className="tile-value skeleton-block skeleton-line-long" />

      </div>

    </div>

  );

}


/* =====================================================
   EMPTY STATE
===================================================== */

function EmptyTiles({ message }) {

  return (

    <div className="overview-empty">

      <div className="overview-empty-icon">

        <Inbox size={22} />

      </div>

      <p>{message}</p>

    </div>

  );

}
function JobcardTooltip({
  active,
  payload,
  total
}) {

  if (!active || !payload?.length) {
    return null;
  }

  const item = payload[0]?.payload;

  if (!item) {
    return null;
  }

  const count = Number(item.count || 0);

  const percentage =
    total > 0
      ? ((count / total) * 100).toFixed(1)
      : 0;

  return (

    <div className="claims-tooltip">

      <strong>
        {item.title}
      </strong>

      <span>
        Count: {count}
      </span>

      <span>
        {percentage}%
      </span>

    </div>

  );

}

/* =====================================================
   OVERVIEW TAB
===================================================== */

export default function OverviewTab({
  data,
  loading = false,
  onTabChange
}) {


  /* =====================================================
     API DATA
  ===================================================== */
const pipeline = data?.pipeline || [];


  const summaries =
    data?.summaries || [];


  /* NEW WORKSHOP FUNCTION DATA */
const totalClaims =
  summaries.find(
    (item) => item.type === "claims"
  )?.value ?? 0;


// Only stages with claims appear in donut

const activePipeline = pipeline.filter(
  (item) => (item.count ?? 0) > 0
);

const pipelineTotal = activePipeline.reduce(
  (total, item) => total + Number(item.count || 0),
  0
);
// Add percentage for legend

const pipelineWithPercentage = pipeline.map(
  (item) => ({
    ...item,

    percentage:
      totalClaims > 0
        ? Math.round(
            ((item.count ?? 0) / totalClaims) * 100
          )
        : 0,
  })
); 
 const workshop =
    data?.workshop_dashboard || {};


  const hasWorkshopData =
    workshop &&
    Object.keys(workshop).length > 0;

  const jobcardPipeline = data?.jobcard_pipeline || [];

 // const activeJobCards = data?.active_job_cards ?? 0;


  // Remove stages with 0 count
  const activeJobcardPipeline = jobcardPipeline.filter(
    item => Number(item.count) > 0
  );

  const activeJobCards = activeJobcardPipeline.reduce(
    (total, item) =>
      total + Number(item.count || 0),
    0
  );

  const pipelineWithPercentagejb = jobcardPipeline.map(
  (item) => ({
    ...item,

    percentage:
      activeJobCards > 0
        ? Math.round(
            ((item.count ?? 0) / activeJobCards) * 100
          )
        : 0,
  })
); 
  /* =====================================================
     WORKSHOP PERFORMANCE CARDS
  ===================================================== */

  const performanceCards = [

    {
      key: "total_jobs",
      title: "Total Jobs",
      value: workshop.total_jobs ?? 0,
      color: "#2563EB",
    },

    {
      key: "total_vehicles",
      title: "Total Vehicles",
      value: workshop.total_vehicles ?? 0,
      color: "#0891B2",
    },

    {
      key: "pending_jobs",
      title: "Pending Jobs",
      value: workshop.pending_jobs ?? 0,
      color: "#F59E0B",
    },

    {
      key: "running_jobs",
      title: "Running Jobs",
      value: workshop.running_jobs ?? 0,
      color: "#8B5CF6",
    },

    {
      key: "completed_jobs",
      title: "Completed Jobs",
      value: workshop.completed_jobs ?? 0,
      color: "#16A34A",
    },

    {
      key: "ready_for_delivery",
      title: "Ready for Delivery",
      value: workshop.ready_for_delivery ?? 0,
      color: "#0EA5E9",
    },

    {
      key: "completion_percentage",
      title: "Completion Rate",
      value: `${workshop.completion_percentage ?? 0}%`,
      color: "#EC4899",
    },

    {
      key: "average_tat",
      title: "Average TAT",
      value: `${workshop.average_tat ?? 0} Days`,
      color: "#14B8A6",
    },

  ];


  /* =====================================================
     MANAGEMENT ATTENTION DATA
  ===================================================== */

  const attentionCards = [

    {
      key: "overdue_jobs",
      title: "Overdue Jobs",
      value: workshop.overdue_jobs ?? 0,
      icon: AlertTriangle,
      color: "#DC2626",
    },

    {
      key: "qc_pending",
      title: "QC Pending",
      value: workshop.qc_pending ?? 0,
      icon: ClipboardCheck,
      color: "#F59E0B",
    },

    {
      key: "road_test_pending",
      title: "Road Test Pending",
      value: workshop.road_test_pending ?? 0,
      icon: Gauge,
      color: "#8B5CF6",
    },

    {
      key: "washing_pending",
      title: "Washing Pending",
      value: workshop.washing_pending ?? 0,
      icon: Car,
      color: "#0EA5E9",
    },

  ];

  const renderDonutLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percentage,
}) => {

  const RADIAN = Math.PI / 180;

  const radius =
    innerRadius +
    (outerRadius - innerRadius) * 0.55;

  const x =
    cx +
    radius *
    Math.cos(-midAngle * RADIAN);

  const y =
    cy +
    radius *
    Math.sin(-midAngle * RADIAN);

  // Hide labels for very small slices

  if (percentage < 8) {
    return null;
  }
  
  return (

    <text
      x={x}
      y={y}
      fill="#ffffff"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={700}
      pointerEvents="none"
    >

      {percentage}%

    </text>

  );

};
  return (

    <div className="overview-dashboard">


      {/* =====================================================
          OVERVIEW SUMMARY
      ===================================================== */}

<section className="overview-panel operation-panel claims-summary-panel" onClick={() => {
    window.location.href = "/claimList/";
  }}>

  {/* HEADER */}

  <div className="overview-panel-header">

    <div>

      <h2>Claims Overview</h2>

      <p>
        Current claim workflow and stage distribution
      </p>

    </div>


    <div className="claims-total-box">

      <span>Total Claims</span>

      <strong>{totalClaims}</strong>

    </div>

  </div>



  {/* CONTENT */}

  {loading ? (

    <div className="claims-chart-loading">

      <div className="claims-donut-skeleton skeleton-block" />

    </div>

  ) : pipeline.length === 0 ? (

    <EmptyTiles
      message="No claim stage data to show yet."
    />

  ) : (

    <div className="claims-chart-layout">

  {/* ================= DONUT ================= */}

  <div className="claims-donut-wrapper">

    <ResponsiveContainer
      width="100%"
      height={380}
    >

      <PieChart>

        <Pie
          data={pipelineWithPercentage}
          dataKey="count"
          nameKey="title"

          cx="50%"
          cy="50%"

          innerRadius={90}
          outerRadius={140}

          paddingAngle={2}

          stroke="#ffffff"
          strokeWidth={2}

          label={renderDonutLabel}
          labelLine={false}
        >

          {pipelineWithPercentage.map(
            (entry, index) => (

              <Cell
                key={`cell-${index}`}
                fill={entry.color}
              />

            )
          )}

        </Pie>


        <Tooltip
          content={<ClaimsTooltip />}
        />

      </PieChart>

    </ResponsiveContainer>


    {/* CENTER TOTAL */}

    <div className="claims-donut-center">

      <strong>
        {pipelineTotal}
      </strong>

      <span>
        Total Claims
      </span>

    </div>

  </div>



  {/* ================= STAGE LEGEND ================= */}

  <div className="claims-stage-legend">

    <h3>
      Claim Stages
    </h3>


    <div className="claims-stage-list">

       {pipelineWithPercentage
    .filter((item) => Number(item.count) > 0)
    .map((item) => (

        <div
          className="claims-stage-item"
          key={item.stage}
        >

          <div className="claims-stage-name">

            <span
              className="claims-stage-dot"
              style={{
                backgroundColor: item.color
              }}
            />

            <span className="claims-stage-title">
              {item.title}
            </span>

          </div>


          <strong className="claims-stage-count">

            {item.count}

          </strong>

        </div>

      ))}

    </div>

  </div>

</div>
  )}


  {/* FOOTER */}

  <div className="claims-distribution-footer">

    <BarChart3 size={17} />

    <span>
      Distribution of claims across different workflow stages
    </span>

  </div>

</section>    


{/* ================= JOBCARD OVERVIEW ================= */}

<section className="overview-panel operation-panel claims-summary-panel" onClick={() => {
    window.location.href = "/jobList/";
  }}>

  {/* HEADER */}

  <div className="overview-panel-header">

    <div>

      <h2>Jobcards Overview</h2>

      <p>
        Current jobcard workflow and stage distribution
      </p>

    </div>


    <div className="claims-total-box">

      <span>Total Active Jobcards</span>

      <strong>{activeJobCards}</strong>

    </div>

  </div>



  {/* CONTENT */}

  {loading ? (

    <div className="claims-chart-loading">

      <div className="claims-donut-skeleton skeleton-block" />

    </div>

  ) : activeJobcardPipeline.length === 0 ? (

    <EmptyTiles
      message="No active jobcard stage data to show yet."
    />

  ) : (

    <div className="claims-chart-layout">

  {/* ================= DONUT ================= */}

  <div className="claims-donut-wrapper">

    <ResponsiveContainer
      width="100%"
      height={380}
    >

      <PieChart>

        <Pie
          data={pipelineWithPercentagejb}
          dataKey="count"
          nameKey="title"

          cx="50%"
          cy="50%"

          innerRadius={90}
          outerRadius={140}

          paddingAngle={2}

          stroke="#ffffff"
          strokeWidth={2}

          label={renderDonutLabel}
          labelLine={false}
        >

          {pipelineWithPercentagejb.map(
            (entry, index) => (

              <Cell
                key={`cell-${index}`}
                fill={entry.color}
              />

            )
          )}

        </Pie>


        <Tooltip
          content={<ClaimsTooltip />}
        />

      </PieChart>

    </ResponsiveContainer>


    {/* CENTER TOTAL */}

    <div className="claims-donut-center">

      <strong>
        {activeJobCards}
      </strong>

      <span>
        Total Active Jobcards
      </span>

    </div>

  </div>



  {/* ================= STAGE LEGEND ================= */}

  <div className="claims-stage-legend">

    <h3>
      Jobcard Stages
    </h3>


    <div className="claims-stage-list">

       {pipelineWithPercentagejb
    .filter((item) => Number(item.count) > 0)
    .map((item) => (

        <div
          className="claims-stage-item"
          key={item.stage}
        >

          <div className="claims-stage-name">

            <span
              className="claims-stage-dot"
              style={{
                backgroundColor: item.color
              }}
            />

            <span className="claims-stage-title">
              {item.title}
            </span>

          </div>


          <strong className="claims-stage-count">

            {item.count}

          </strong>

        </div>

      ))}

    </div>

  </div>

</div>
  )}


  {/* FOOTER */}

  <div className="claims-distribution-footer">

    <BarChart3 size={17} />

    <span>
      Distribution of active jobcards across different workflow stages
    </span>

  </div>

</section>    



      {/* =====================================================
          WORKSHOP PERFORMANCE
      ===================================================== */}

      <section className="overview-panel performance-panel">


        <div className="overview-panel-header">

          <div>

            <h2>
              Workshop Performance
            </h2>

            <p>
              Current workshop operations and efficiency
            </p>

          </div>


          <div className="panel-header-icon performance-header-icon">

            <Activity size={20} />

          </div>

        </div>


        {loading ? (

          <div className="overview-tiles">

            {Array.from({
              length: 8
            }).map((_, i) => (

              <SkeletonTile key={i} />

            ))}

          </div>

        ) : !hasWorkshopData ? (

          <EmptyTiles
            message="No workshop performance data available."
          />

        ) : (

          <div className="overview-tiles">

            {performanceCards.map((item) => {

              const Icon =
                performanceIcons[item.key] || Activity;


              return (

                <div
  className="overview-tile performance-tile clickable-tile"
  key={item.key}

  role="button"

  tabIndex={0}

  onClick={() => {

    const targetTab =
      performanceTabMapping[item.key];

    if (targetTab && onTabChange) {

      onTabChange(targetTab);

    }

  }}

  style={{
    "--tile-color": item.color
  }}
>

                  <div className="tile-icon">

                    <Icon size={21} />

                  </div>


                  <div className="tile-content">

                    <span className="tile-label">

                      {item.title}

                    </span>


                    <strong className="tile-value">

                      {item.value}

                    </strong>

                  </div>

                </div>

              );

            })}

          </div>

        )}

      </section>



      {/* =====================================================
          MANAGEMENT ATTENTION
      ===================================================== */}

      <section className="overview-panel attention-panel">


        <div className="overview-panel-header">

          <div>

            <h2>
              Management Attention
            </h2>

            <p>
              Operational items requiring attention
            </p>

          </div>


          <div className="panel-header-icon attention-header-icon">

            <AlertTriangle size={20} />

          </div>

        </div>


        {loading ? (

          <div className="overview-tiles">

            {Array.from({
              length: 4
            }).map((_, i) => (

              <SkeletonTile key={i} />

            ))}

          </div>

        ) : !hasWorkshopData ? (

          <EmptyTiles
            message="No management alerts available."
          />

        ) : (

          <div className="overview-tiles">

            {attentionCards.map((item) => {

              const Icon = item.icon;


              return (

                <div
                  className="overview-tile attention-tile"
                  key={item.key}
                  style={{
                    "--tile-color": item.color
                  }}
                >

                  <div className="tile-icon">

                    <Icon size={21} />

                  </div>


                  <div className="tile-content">

                    <span className="tile-label">

                      {item.title}

                    </span>


                    <strong className="tile-value">

                      {item.value}

                    </strong>

                  </div>

                </div>

              );

            })}

          </div>

        )}

      </section>
     
    </div>
    

  );

}