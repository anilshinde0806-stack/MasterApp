import React, { useMemo } from "react";

import {
  AlertTriangle,
  ShieldAlert,
  ClipboardList,
  Wrench,
  Truck,
  CheckCircle2,
  BellRing,
  Activity,
  CircleAlert,
  TrendingDown,
  ArrowRight,
} from "lucide-react";

import "./ManagementAlertsTab.css";


export default function ManagementAlertsTab({
  data,
  onNavigate,
}) {

  const alerts = useMemo(() => {

    const summaries = data?.summaries || [];

    const performance = data?.performance || {};


    // ==========================================
    // GET SUMMARY VALUES
    // ==========================================

    const getSummaryValue = (type) => {

      const item = summaries.find(
        (summary) => summary.type === type
      );

      return Number(item?.value || 0);

    };


    const insurance = getSummaryValue("insurance");

    const survey = getSummaryValue("survey");

    const workshop = getSummaryValue("workshop");

    const delivery = getSummaryValue("delivery");


    const completionPercentage =
      Number(
        performance?.completion_percentage || 0
      );


    const managementAlerts = [];


    // ==========================================
    // INSURANCE ALERT
    // ==========================================
      console.log("Insurance Alert: ", insurance);
    if (insurance > 0) {
     
      managementAlerts.push({

        id: "insurance",

        title: "Insurance Approvals Pending",

        description:
          `${insurance} insurance claim${
            insurance > 1 ? "s require" : " requires"
          } management attention.`,

        value: insurance,

        priority:
          insurance >= 5
            ? "high"
            : "medium",

        category: "Insurance",

        icon: ShieldAlert,
        targetTab: "insurance",
      });

    }


    // ==========================================
    // SURVEY ALERT
    // ==========================================

    if (survey > 0) {

      managementAlerts.push({

        id: "survey",

        title: "Survey Cases Pending",

        description:
          `${survey} vehicle survey${
            survey > 1 ? " cases are" : " case is"
          } awaiting completion.`,

        value: survey,

        priority:
          survey >= 5
            ? "high"
            : "medium",

        category: "Survey",

        icon: ClipboardList,
        targetTab: "workshop",

      });

    }


    // ==========================================
    // WORKSHOP ALERT
    // ==========================================

    if (workshop > 0) {

      managementAlerts.push({

        id: "workshop",

        title: "Vehicles in Workshop",

        description:
          `${workshop} vehicle${
            workshop > 1 ? "s are" : " is"
          } currently under repair.`,

        value: workshop,

        priority:
          workshop >= 10
            ? "high"
            : "normal",

        category: "Workshop",

        icon: Wrench,

      });

    }


    // ==========================================
    // DELIVERY STATUS
    // ==========================================

    if (delivery > 0) {

      managementAlerts.push({

        id: "delivery",

        title: "Vehicles Ready for Delivery",

        description:
          `${delivery} vehicle${
            delivery > 1 ? "s are" : " is"
          } ready for customer delivery.`,

        value: delivery,

        priority: "success",

        category: "Delivery",

        icon: Truck,

      });

    }


    // ==========================================
    // LOW COMPLETION PERFORMANCE
    // ==========================================

    if (
      performance?.total_jobs > 0 &&
      completionPercentage < 50
    ) {

      managementAlerts.push({

        id: "performance",

        title: "Low Workshop Completion Rate",

        description:
          `Workshop completion is currently at ${completionPercentage.toFixed(1)}%. Performance requires attention.`,

        value: `${completionPercentage.toFixed(1)}%`,

        priority: "high",

        category: "Performance",

        icon: TrendingDown,
        targetTab: "workshop",
      });

    }


    return managementAlerts;

  }, [data]);


  // ==========================================
  // ALERT COUNTS
  // ==========================================

  const highPriority =
    alerts.filter(
      (alert) => alert.priority === "high"
    ).length;


  const mediumPriority =
    alerts.filter(
      (alert) => alert.priority === "medium"
    ).length;


  const normalPriority =
    alerts.filter(
      (alert) =>
        alert.priority === "normal"
    ).length;


  const successAlerts =
    alerts.filter(
      (alert) =>
        alert.priority === "success"
    ).length;


  return (

    <div className="management-alerts-dashboard">


      {/* ======================================
          HEADER
      ====================================== */}

      <div className="management-alerts-header">


        <div>

          <div className="management-title-row">

            <div className="management-header-icon">

              <BellRing size={22} />

            </div>


            <div>

              <h2>
                Management Alerts
              </h2>


              <p>
                Important operational issues requiring attention
              </p>

            </div>

          </div>

        </div>


        <div className="alerts-total-badge">

          <Activity size={15} />

          {alerts.length} Active

        </div>


      </div>



      {/* ======================================
          ALERT SUMMARY
      ====================================== */}

      <section className="alert-summary-grid">


        <AlertSummaryCard
          title="Critical Attention"
          value={highPriority}
          subtitle="High priority issues"
          icon={CircleAlert}
          type="critical"
        />


        <AlertSummaryCard
          title="Pending Actions"
          value={mediumPriority}
          subtitle="Requires follow-up"
          icon={AlertTriangle}
          type="warning"
        />


        <AlertSummaryCard
          title="Operational Status"
          value={normalPriority}
          subtitle="Currently active"
          icon={Activity}
          type="info"
        />


        <AlertSummaryCard
          title="Positive Updates"
          value={successAlerts}
          subtitle="Ready or completed"
          icon={CheckCircle2}
          type="success"
        />


      </section>



      {/* ======================================
          MAIN ALERT PANEL
      ====================================== */}

      <section className="alerts-main-grid">


        {/* ====================================
            ACTIVE ALERTS
        ==================================== */}

        <div className="alerts-panel">


          <div className="alerts-panel-header">

            <div>

              <h3>
                Active Management Alerts
              </h3>

              <p>
                Review operational issues across the selected dashboard filters
              </p>

            </div>


            <span className="alerts-count">

              {alerts.length}

            </span>

          </div>



          <div className="alerts-list">


            {alerts.length > 0 ? (

              alerts.map((alert) => (

               <ManagementAlertCard
                key={alert.id}
                alert={alert}
                onNavigate={onNavigate}
              />

              ))

            ) : (

              <div className="no-alerts">

                <div className="no-alert-icon">

                  <CheckCircle2 size={38} />

                </div>


                <h3>
                  Everything Looks Good!
                </h3>


                <p>
                  No management alerts were found for the selected period.
                </p>

              </div>

            )}

          </div>


        </div>



        {/* ====================================
            MANAGEMENT STATUS
        ==================================== */}

        <div className="management-status-panel">


          <div className="management-status-header">

            <h3>
              Management Status
            </h3>


            <span>
              Live Overview
            </span>

          </div>



          <ManagementStatusRow
            label="High Priority"
            value={highPriority}
            type="danger"
          />


          <ManagementStatusRow
            label="Pending Follow-ups"
            value={mediumPriority}
            type="warning"
          />


          <ManagementStatusRow
            label="Operational Activities"
            value={normalPriority}
            type="info"
          />


          <ManagementStatusRow
            label="Positive Updates"
            value={successAlerts}
            type="success"
          />



          <div className="management-status-footer">

            <strong>
              Overall Dashboard Status
            </strong>


            <div
              className={`overall-status ${
                highPriority > 0
                  ? "needs-attention"
                  : "healthy"
              }`}
            >

              {highPriority > 0
                ? "Needs Attention"
                : "Healthy"}

            </div>

          </div>


        </div>


      </section>


    </div>

  );

}



/* ==========================================
   ALERT SUMMARY CARD
========================================== */

function AlertSummaryCard({
  title,
  value,
  subtitle,
  icon: Icon,
  type,
}) {

  return (

    <div
      className={`alert-summary-card ${type}`}
    >


      <div className="alert-summary-icon">

        <Icon size={21} />

      </div>


      <div className="alert-summary-content">

        <span>
          {title}
        </span>


        <strong>
          {value}
        </strong>


        <small>
          {subtitle}
        </small>

      </div>


    </div>

  );

}



/* ==========================================
   MANAGEMENT ALERT CARD
========================================== */

function ManagementAlertCard({
  alert,
  onNavigate,
}) {

  const Icon = alert.icon;


  const handleNavigate = () => {

    if (
      alert.targetTab &&
      onNavigate
    ) {

      onNavigate(alert.targetTab);

    }

  };


  return (

    <div
      className={`management-alert-card ${alert.priority} clickable`}
      onClick={handleNavigate}
    >


      <div className="management-alert-icon">

        <Icon size={21} />

      </div>


      <div className="management-alert-content">


        <div className="management-alert-title-row">

          <h4>
            {alert.title}
          </h4>


          <span
            className={`priority-badge ${alert.priority}`}
          >

            {getPriorityLabel(alert.priority)}

          </span>

        </div>


        <p>
          {alert.description}
        </p>


        <div className="management-alert-footer">


          <span>
            {alert.category}
          </span>


          <button
            onClick={(e) => {

              e.stopPropagation();

              handleNavigate();

            }}
          >

            View Details

            <ArrowRight size={14} />

          </button>


        </div>


      </div>


      <div className="management-alert-value">

        {alert.value}

      </div>


    </div>

  );

}





/* ==========================================
   MANAGEMENT STATUS ROW
========================================== */

function ManagementStatusRow({
  label,
  value,
  type,
}) {

  return (

    <div className="management-status-row">


      <div className="management-status-label">

        <span
          className={`status-dot ${type}`}
        />

        {label}

      </div>


      <strong>

        {value}

      </strong>


    </div>

  );

}



/* ==========================================
   HELPERS
========================================== */

function getPriorityLabel(priority) {

  const labels = {

    high: "High",

    medium: "Medium",

    normal: "Active",

    success: "Ready",

  };


  return labels[priority] || "Info";

}