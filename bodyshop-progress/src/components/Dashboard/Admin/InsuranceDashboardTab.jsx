import React from "react";

import "./InsuranceDashboardTab.css";

import {
  ShieldCheck,
  FileText,
  ClipboardCheck,
  Camera,
  CheckCircle2,
  Clock3,
  AlertCircle,
  Building2,
  ChevronRight,
  BarChart3,
} from "lucide-react";


export default function InsuranceDashboardTab({ data }) {

  const pipeline = data?.pipeline || [];

  const summaries = data?.summaries || [];


  // ==========================================
  // GET SUMMARY VALUE
  // ==========================================

  const getSummary = (type) => {

    const item = summaries.find(
      (summary) => summary.type === type
    );

    return Number(item?.value || 0);

  };


  const claims = getSummary("claims");

  const insurance = getSummary("insurance");

  const survey = getSummary("survey");

  const delivery = getSummary("delivery");


  // ==========================================
  // INSURANCE KPI CARDS
  // ==========================================

  const insuranceCards = [

    {
      title: "Open Claims",
      value: claims,
      icon: FileText,
      color: "#2563EB",
    },

    {
      title: "Insurance Approval",
      value: insurance,
      icon: ShieldCheck,
      color: "#DC2626",
    },

    {
      title: "Survey Pending",
      value: survey,
      icon: Camera,
      color: "#0891B2",
    },

    {
      title: "Ready for Delivery",
      value: delivery,
      icon: CheckCircle2,
      color: "#16A34A",
    },

  ];


  // ==========================================
  // PIPELINE TOTAL
  // ==========================================

  const pipelineTotal = pipeline.reduce(
    (total, item) =>
      total + Number(item.count || 0),
    0
  );


  return (

    <div className="insurance-dashboard">


      {/* ======================================
          HEADER
      ====================================== */}

      <div className="insurance-dashboard-header">

        <div>

          <h2>Insurance Dashboard</h2>

          <p>
            Monitor claims, surveys and insurance approval workflow
          </p>

        </div>


        <div className="insurance-header-icon">

          <ShieldCheck size={23} />

        </div>

      </div>



      {/* ======================================
          KPI CARDS
      ====================================== */}

      <section className="insurance-kpi-grid">

        {insuranceCards.map((card) => {

          const Icon = card.icon;

          return (

            <div
              className="insurance-kpi-card"
              key={card.title}
              style={{
                "--insurance-color": card.color
              }}
            >

              <div className="insurance-kpi-icon">

                <Icon size={22} />

              </div>


              <div className="insurance-kpi-content">

                <span>
                  {card.title}
                </span>

                <strong>
                  {card.value}
                </strong>

              </div>

            </div>

          );

        })}

      </section>



      {/* ======================================
          CLAIM PIPELINE
      ====================================== */}

      <section className="insurance-main-grid">


        {/* PIPELINE */}

        <div className="insurance-panel insurance-pipeline-panel">


          <div className="insurance-panel-header">

            <div>

              <h3>Claim Pipeline</h3>

              <p>
                Current claim workflow across all stages
              </p>

            </div>


            <BarChart3 size={21} />

          </div>



          <div className="claim-pipeline-list">


            {pipeline.length > 0 ? (

              pipeline.map((item, index) => {

                const count = Number(item.count || 0);

                const percentage =
                  pipelineTotal > 0
                    ? (count / pipelineTotal) * 100
                    : 0;


                return (

                  <React.Fragment
                    key={
                      item.stage ||
                      item.title ||
                      index
                    }
                  >

                    <div
                      className="claim-stage-card"
                      style={{
                        "--stage-color":
                          item.color || "#2563EB"
                      }}
                    >


                      <div className="claim-stage-left">


                        <div className="claim-stage-icon">

                          <FileText size={17} />

                        </div>


                        <div>

                          <strong>

                            {item.title ||
                              "Claim Stage"}

                          </strong>


                          <span>

                            {percentage.toFixed(1)}%
                            {" "}of pipeline

                          </span>

                        </div>

                      </div>



                      <div className="claim-stage-right">

                        <strong>

                          {count}

                        </strong>


                        <div className="claim-stage-progress">

                          <div
                            className="claim-stage-progress-fill"
                            style={{
                              width:
                                `${percentage}%`
                            }}
                          />

                        </div>

                      </div>


                    </div>


                    {index < pipeline.length - 1 && (

                      <div className="claim-pipeline-arrow">

                        <ChevronRight size={18} />

                      </div>

                    )}

                  </React.Fragment>

                );

              })

            ) : (

              <div className="insurance-empty-state">

                <ClipboardCheck size={34} />

                <strong>
                  No Pipeline Data
                </strong>

                <span>
                  Claim stages will appear here
                </span>

              </div>

            )}

          </div>


        </div>



        {/* CLAIM STATUS */}

        <div className="insurance-panel insurance-status-panel">


          <div className="insurance-panel-header">

            <div>

              <h3>Claim Status</h3>

              <p>
                Important insurance workflow indicators
              </p>

            </div>


            <Building2 size={21} />

          </div>



          <div className="insurance-status-list">


            <InsuranceStatusItem
              title="Open Claims"
              value={claims}
              icon={FileText}
              color="#2563EB"
            />


            <InsuranceStatusItem
              title="Awaiting Insurance Approval"
              value={insurance}
              icon={Clock3}
              color="#DC2626"
            />


            <InsuranceStatusItem
              title="Survey Pending"
              value={survey}
              icon={Camera}
              color="#0891B2"
            />


            <InsuranceStatusItem
              title="Ready for Delivery"
              value={delivery}
              icon={CheckCircle2}
              color="#16A34A"
            />


          </div>


          {/* ALERT */}

          {(insurance > 0 || survey > 0) && (

            <div className="insurance-alert">

              <AlertCircle size={19} />

              <div>

                <strong>
                  Attention Required
                </strong>

                <span>

                  {insurance + survey}
                  {" "}claim(s) require insurance
                  or survey action.

                </span>

              </div>

            </div>

          )}


        </div>


      </section>


    </div>

  );

}



/* ==========================================
   INSURANCE STATUS ITEM
========================================== */

function InsuranceStatusItem({
  title,
  value,
  icon: Icon,
  color
}) {

  return (

    <div
      className="insurance-status-item"
      style={{
        "--status-color": color
      }}
    >

      <div className="insurance-status-left">

        <div className="insurance-status-icon">

          <Icon size={18} />

        </div>


        <span>

          {title}

        </span>

      </div>


      <strong>

        {value}

      </strong>

    </div>

  );

}