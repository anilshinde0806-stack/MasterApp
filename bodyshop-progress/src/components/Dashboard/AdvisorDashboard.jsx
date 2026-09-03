import { useEffect, useState } from "react";

import "./AdvisorDashboard.css";


export default function AdvisorDashboard() {

  const [data, setData] = useState({
  welcome_message: "",
  assigned_jobs: 0,
  pending_jobs: 0,
  completed_jobs: 0,

  summaries: [],

  performance: {
    completion_percentage: 0,
    completed: 0,
    running: 0,
    pending: 0,
  },

  recent_work: [],
});


  const [loading, setLoading] = useState(true);


  useEffect(() => {

    async function loadAdvisorDashboard() {

      try {

        const response = await fetch(
          "/ajax/advisor-dashboard-data/",
          {
            credentials: "same-origin",
          }
        );


        if (!response.ok) {

          throw new Error(
            `HTTP ${response.status}`
          );

        }


        const result = await response.json();


        if (!result.success) {

          throw new Error(
            result.message ||
            "Unable to load Advisor Dashboard"
          );

        }


        setData(result);

      } catch (error) {

        console.error(
          "Advisor Dashboard API error:",
          error
        );

      } finally {

        setLoading(false);

      }

    }


    loadAdvisorDashboard();

  }, []);


  if (loading) {

    return (

      <div className="dashboard-loading">

        Loading Advisor Dashboard...

      </div>

    );

  }


  const today = new Date();


  const dateText = today.toLocaleDateString(
    "en-IN",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
  );


  const dayText = today.toLocaleDateString(
    "en-IN",
    {
      weekday: "long",
    }
  );

  const performance = {
  completion_percentage: data.performance?.completion_percentage ?? 0,
  completed: data.performance?.completed ?? 0,
  running: data.performance?.running ?? 0,
  pending: data.performance?.pending ?? 0,
};
const recent_work = Array.isArray(data.recent_work)
  ? data.recent_work
  : [];
  return (

    <div className="advisor-mobile">


      {/* WELCOME */}

      <div className="am-card am-welcome">

        <div className="am-welcome-left">

          <div className="am-icon">

            <i className="fa-solid fa-user-tie"></i>

          </div>


          <div>

            <span>
              Good Morning! 👋
            </span>

            <h2>
              {data.welcome_message}
            </h2>

            <p>
              Here's what's happening in your workshop.
            </p>

          </div>

        </div>


        <div className="am-date">

          <div className="am-date-icon">

            <i className="fa-solid fa-calendar"></i>

          </div>


          <div>

            {dateText}

            <small>
              {dayText}
            </small>

          </div>

        </div>

      </div>



      {/* FEATURE CARDS */}

      <div className="am-feature-grid">


        <a
          className="am-card am-feature blue"
          href="/jobList/"
        >

          <div>

            <h3>
              Job Cards
            </h3>

            <p>
              Create, view & manage job cards
            </p>

          </div>


          <span className="am-arrow">
            ›
          </span>

        </a>



        <a
          className="am-card am-feature green"
          href="/claimList/"
        >

          <div>

            <h3>
              Claims
            </h3>

            <p>
              Insurance claims management
            </p>

          </div>


          <span className="am-arrow">
            ›
          </span>

        </a>


      </div>



      {/* QUICK TILES */}

      <div className="am-tiles">


        <div className="am-card am-tile">

          <div className="am-tile-icon">
            <i className="fa-solid fa-briefcase"></i>
          </div>

          <strong>
            {data.assigned_jobs}
          </strong>

          <span>
            Assigned Jobs
          </span>

        </div>



        <div className="am-card am-tile">

          <div className="am-tile-icon">
            <i className="fa-solid fa-clock"></i>
          </div>

          <strong>
            {data.pending_jobs}
          </strong>

          <span>
            Pending Jobs
          </span>

        </div>



        <div className="am-card am-tile">

          <div className="am-tile-icon">
            <i className="fa-solid fa-circle-check"></i>
          </div>

          <strong>
            {data.completed_jobs}
          </strong>

          <span>
            Completed Jobs
          </span>

        </div>



        <div className="am-card am-tile">

          <div className="am-tile-icon">
            <i className="fa-solid fa-car"></i>
          </div>

          <strong>
            {data.ready_jobs}
          </strong>

          <span>
            Ready Delivery
          </span>

        </div>


      </div>



      {/* TODAY STATUS */}

      <section className="am-card am-section">

        <div className="am-section-head">

          <h3>
            Today's Status
          </h3>

        </div>


        <div className="am-stats">


          <div className="am-stat">

            <span className="am-stat-icon">
              <i className="fa-solid fa-briefcase"></i>
            </span>

            <strong>
              {data.assigned_jobs}
            </strong>

            <small>
              Assigned
            </small>

          </div>



          <div className="am-stat">

            <span className="am-stat-icon">
              <i className="fa-solid fa-clock"></i>
            </span>

            <strong>
              {data.pending_jobs}
            </strong>

            <small>
              Pending
            </small>

          </div>



          <div className="am-stat">

            <span className="am-stat-icon">
              <i className="fa-solid fa-check"></i>
            </span>

            <strong>
              {data.completed_jobs}
            </strong>

            <small>
              Completed
            </small>

          </div>



          <div className="am-stat">

            <span className="am-stat-icon">
              <i className="fa-solid fa-truck"></i>
            </span>

            <strong>
              {data.ready_jobs}
            </strong>

            <small>
              Ready
            </small>

          </div>


        </div>

      </section>



      {/* WORKSHOP PERFORMANCE */}

      <section className="am-card am-section">

        <div className="am-section-head">

          <h3>
            Workshop Performance
          </h3>

          <span className="am-link">
            This Month
          </span>

        </div>


        <div className="am-kpis">


          <div className="am-kpi">

            <small>
              Completion
            </small>

            <strong>
              {performance.completion_percentage}%
            </strong>


            <div className="am-bar">

              <i
                style={{
                  width:
                    `${performance.completion_percentage}%`
                }}
              />

            </div>


            <small>
              {performance.completed} completed
            </small>

          </div>



          <div className="am-kpi">

            <small>
              Running
            </small>

            <strong>
              {performance.running}
            </strong>


            <div className="am-bar">

              <i
                className="running-bar"
                style={{
                  width: "60%"
                }}
              />

            </div>


            <small>
              Work in progress
            </small>

          </div>



          <div className="am-kpi">

            <small>
              Pending
            </small>

            <strong>
              {performance.pending}
            </strong>


            <div className="am-bar">

              <i
                className="pending-bar"
                style={{
                  width: "35%"
                }}
              />

            </div>


            <small>
              Awaiting start
            </small>

          </div>


        </div>

      </section>



      {/* RECENT JOBS */}

      <section className="am-card am-section">

        <div className="am-section-head">

          <h3>
            Recent Job Cards
          </h3>


          <a
            className="am-link"
            href="/jobList/"
          >
            View all ›
          </a>

        </div>



        {recent_work.length === 0 ? (

          <p className="am-empty">

            No recent job cards.

          </p>

        ) : (

          recent_work.map((work) => (

            <div
              className="am-job"
              key={work.job_no}
            >

              <i className="am-dot"></i>


              <div>

                <b>
                  {work.vehicle_no}
                </b>

                <small>
                  Claim: {work.claim_no}
                </small>

              </div>


              <div>

                <b>
                  {work.job_no}
                </b>

                <small>
                  {work.status}
                </small>

              </div>


              <span className="am-status">

                {work.progress}%

              </span>

            </div>

          ))

        )}

      </section>


    </div>

  );

}