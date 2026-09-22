import React from "react";

import "./TopPerformanceTab.css";

import {
  Trophy,
  Medal,
  Crown,
  UserRound,
  Wrench,
  BriefcaseBusiness,
  IndianRupee,
  TrendingUp,
  CheckCircle2,
  Award,
} from "lucide-react";


export default function TopPerformanceTab({ data }) {

  const advisors = data?.top_advisors || [];

  const technicians = data?.top_technicians || [];


  return (

    <div className="top-performance-dashboard">


      {/* ======================================
          HEADER
      ====================================== */}

      <div className="top-performance-header">

        <div>

          <h2>Top Performance</h2>

          <p>
            Recognize the best-performing advisors and workshop professionals
          </p>

        </div>


        <div className="top-performance-header-icon">

          <Trophy size={23} />

        </div>

      </div>



      {/* ======================================
          PERFORMANCE SUMMARY
      ====================================== */}

      <section className="performance-highlight-grid">


        <PerformanceHighlight
          title="Top Advisors"
          value={advisors.length}
          subtitle="Active performers"
          icon={UserRound}
          color="#2563EB"
        />


        <PerformanceHighlight
          title="Top Technicians"
          value={technicians.length}
          subtitle="Workshop performers"
          icon={Wrench}
          color="#F59E0B"
        />


        <PerformanceHighlight
          title="Best Advisor Revenue"
          value={formatCurrency(
            advisors[0]?.revenue || 0
          )}
          subtitle={
            advisors[0]?.name || "No advisor data"
          }
          icon={IndianRupee}
          color="#16A34A"
        />


        <PerformanceHighlight
          title="Best Technician Efficiency"
          value={`${Number(
            technicians[0]?.efficiency || 0
          ).toFixed(1)}%`}
          subtitle={
            technicians[0]?.name ||
            "No technician data"
          }
          icon={TrendingUp}
          color="#8B5CF6"
        />


      </section>



      {/* ======================================
          LEADERBOARDS
      ====================================== */}

      <section className="performance-leaderboard-grid">


        {/* ====================================
            TOP ADVISORS
        ==================================== */}

        <div className="leaderboard-panel">


          <div className="leaderboard-header">

            <div>

              <div className="leaderboard-title-row">

                <Trophy size={19} />

                <h3>Top Advisors</h3>

              </div>


              <p>
                Ranked by revenue and completed jobs
              </p>

            </div>


            <span className="leaderboard-badge">

              {advisors.length} Ranked

            </span>

          </div>



          <div className="leaderboard-list">


            {advisors.length > 0 ? (

              advisors.map((advisor, index) => (

                <AdvisorCard
                  key={advisor.id || index}
                  advisor={advisor}
                  rank={index + 1}
                />

              ))

            ) : (

              <EmptyLeaderboard
                icon={UserRound}
                title="No Advisor Data"
                message="Advisor performance will appear here."
              />

            )}

          </div>


        </div>



        {/* ====================================
            TOP TECHNICIANS
        ==================================== */}

        <div className="leaderboard-panel">


          <div className="leaderboard-header">

            <div>

              <div className="leaderboard-title-row">

                <Wrench size={19} />

                <h3>Top Technicians</h3>

              </div>


              <p>
                Ranked by efficiency and completed jobs
              </p>

            </div>


            <span className="leaderboard-badge technician-badge">

              {technicians.length} Ranked

            </span>

          </div>



          <div className="leaderboard-list">


            {technicians.length > 0 ? (

              technicians.map((technician, index) => (

                <TechnicianCard
                  key={technician.id || index}
                  technician={technician}
                  rank={index + 1}
                />

              ))

            ) : (

              <EmptyLeaderboard
                icon={Wrench}
                title="No Technician Data"
                message="Technician performance will appear here."
              />

            )}

          </div>


        </div>


      </section>


    </div>

  );

}



/* ==========================================
   PERFORMANCE HIGHLIGHT
========================================== */

function PerformanceHighlight({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
}) {

  return (

    <div
      className="performance-highlight-card"
      style={{
        "--performance-color": color
      }}
    >

      <div className="performance-highlight-icon">

        <Icon size={21} />

      </div>


      <div className="performance-highlight-content">

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
   ADVISOR CARD
========================================== */

function AdvisorCard({
  advisor,
  rank
}) {

  return (

    <div className="leaderboard-item advisor-item">


      <RankBadge rank={rank} />


      <div className="leaderboard-avatar advisor-avatar">

        {getInitials(advisor.name)}

      </div>


      <div className="leaderboard-person">

        <strong>

          {advisor.name || "Unknown Advisor"}

        </strong>


        <span>

          <BriefcaseBusiness size={13} />

          {advisor.completed_jobs || 0}
          {" "}completed jobs

        </span>

      </div>


      <div className="leaderboard-metric revenue-metric">

        <IndianRupee size={15} />

        <strong>

          {formatCurrency(advisor.revenue || 0)}

        </strong>

      </div>


    </div>

  );

}



/* ==========================================
   TECHNICIAN CARD
========================================== */

function TechnicianCard({
  technician,
  rank
}) {

  const efficiency =
    Number(
      technician.efficiency || 0
    );


  return (

    <div className="leaderboard-item technician-item">


      <RankBadge rank={rank} />


      <div className="leaderboard-avatar technician-avatar">

        {getInitials(technician.name)}

      </div>


      <div className="leaderboard-person">

        <strong>

          {technician.name ||
            "Unknown Technician"}

        </strong>


        <span>

          <CheckCircle2 size={13} />

          {technician.completed_jobs || 0}
          {" "}completed jobs

        </span>


        {technician.department && (

          <small>

            {technician.department}

          </small>

        )}

      </div>


      <div className="technician-efficiency">

        <strong>

          {efficiency.toFixed(1)}%

        </strong>


        <div className="efficiency-bar">

          <div
            className="efficiency-fill"
            style={{
              width:
                `${Math.min(
                  efficiency,
                  100
                )}%`
            }}
          />

        </div>

      </div>


    </div>

  );

}



/* ==========================================
   RANK BADGE
========================================== */

function RankBadge({ rank }) {

  if (rank === 1) {

    return (

      <div className="rank-badge rank-gold">

        <Crown size={17} />

      </div>

    );

  }


  if (rank === 2) {

    return (

      <div className="rank-badge rank-silver">

        <Medal size={17} />

      </div>

    );

  }


  if (rank === 3) {

    return (

      <div className="rank-badge rank-bronze">

        <Award size={17} />

      </div>

    );

  }


  return (

    <div className="rank-badge rank-default">

      {rank}

    </div>

  );

}



/* ==========================================
   EMPTY LEADERBOARD
========================================== */

function EmptyLeaderboard({
  icon: Icon,
  title,
  message
}) {

  return (

    <div className="leaderboard-empty">

      <Icon size={34} />

      <strong>

        {title}

      </strong>


      <span>

        {message}

      </span>

    </div>

  );

}



/* ==========================================
   HELPERS
========================================== */

function getInitials(name) {

  if (!name) return "?";


  return name
    .split(" ")
    .slice(0, 2)
    .map(
      (part) =>
        part.charAt(0)
    )
    .join("")
    .toUpperCase();

}


function formatCurrency(value) {

  return new Intl.NumberFormat(
    "en-IN",
    {
      maximumFractionDigits: 0
    }
  ).format(
    Number(value || 0)
  );

}