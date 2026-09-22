import React from "react";
import "./WorkshopPerformanceTab.css";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import {
  Car,
  Wrench,
  Hourglass,
  ClipboardCheck,
  CheckCircle2,
  Clock3,
  Timer,
  Target,
  Users,
  Paintbrush,
  Construction,
  AlertTriangle,
  ChevronRight,
  Eye,
} from "lucide-react";


const WorkshopPerformanceTab = ({ data }) => {

  // =====================================================
  // SAFE DATA
  // =====================================================

console.log("FULL DATA:", data);

const workshopData =
  data?.workshop_dashboard || {};

console.log("WORKSHOP DATA:", workshopData);
const performance =
  workshopData.performance || {};

const jobProgress =
  workshopData.job_progress || [];

const manpower =
  workshopData.manpower || {};

const technicians =
  workshopData.technicians || [];

const bottlenecks =
  workshopData.bottlenecks || [];

  
  const manpowerData =
  workshopData.manpower || {};

  // =====================================================
  // SUMMARY CARDS
  // =====================================================

  const summaryCards = [

  {
    title: "Total Jobs",
    value: workshopData.total_jobs || 0,
    icon: Car,
    color: "blue",
  },

  {
    title: "Work In Progress",
    value: workshopData.running_jobs || 0,
    subtitle: `${workshopData.completion_percentage || 0}% completion`,
    icon: Wrench,
    color: "green",
  },

  {
    title: "Awaiting Work",
    value: workshopData.pending_jobs || 0,
    icon: Hourglass,
    color: "orange",
  },

  {
    title: "Ready for Delivery",
    value: workshopData.ready_for_delivery || 0,
    icon: ClipboardCheck,
    color: "purple",
  },

  {
    title: "Completed Jobs",
    value: workshopData.completed_jobs || 0,
    icon: CheckCircle2,
    color: "cyan",
  },

  {
    title: "Overdue Jobs",
    value: workshopData.overdue_jobs || 0,
    icon: Clock3,
    color: "red",
  },

  {
    title: "Avg. TAT",
    value: workshopData.average_tat || 0,
    suffix: " Days",
    icon: Timer,
    color: "blue",
  },

  {
    title: "Completion Rate",
    value: workshopData.completion_percentage || 0,
    suffix: "%",
    icon: Target,
    color: "green",
  },

];


  // =====================================================
  // JOB PROGRESS
  // Replace with API data later
  // =====================================================

  const jobProgressData = workshopData.job_progress || [];
  const filteredJobProgressData =
  jobProgressData.filter(
    item => Number(item.count) > 0
  );

  // =====================================================
  // TECHNICIANS
  // =====================================================

 // const technicians =
   // data?.top_technicians || [];


  // =====================================================
  // MANPOWER
  // =====================================================

  

  // =====================================================
  // ALERTS
  // =====================================================

  const alerts = [

    {
      title: "Insurance Approval Pending",
      value: 10,
      icon: AlertTriangle,
      color: "red",
    },

    {
      title: "Parts Pending",
      value: 7,
      icon: Construction,
      color: "orange",
    },

    {
      title: "Denting Queue",
      value: 9,
      icon: Users,
      color: "orange",
    },

    {
      title: "Painting Queue",
      value: 6,
      icon: Paintbrush,
      color: "orange",
    },

    {
      title: "Quality Check Pending",
      value: 5,
      icon: CheckCircle2,
      color: "green",
    },

  ];
    
  const handleJobProgressClick = (data) => {

  const stage =
    data?.stage ||
    data?.payload?.stage;

  if (!stage) return;

  navigate(
    `/jobcardList/?stage=${encodeURIComponent(stage)}`
  );

};

  return (

    <div className="workshop-dashboard">


      {/* ========================================= */}
      {/* TOP SUMMARY CARDS */}
      {/* ========================================= */}

      <div className="workshop-summary-grid">

        {summaryCards.map((item, index) => {

          const Icon = item.icon;

          return (

            <div
              className={`workshop-summary-card ${item.color}`}
              key={index}
            >

              <div className="summary-icon">

                <Icon size={30} />

              </div>


              <div className="summary-content">

                <div className="summary-title">

                  {item.title}

                </div>


                <div className="summary-value">

                  {item.value}
                  {item.suffix}

                </div>


                <div className="summary-subtitle">

                  {item.subtitle}

                </div>


                {item.progress !== undefined && (

                  <div className="mini-progress">

                    <div
                      className="mini-progress-fill"
                      style={{
                        width: `${item.progress}%`
                      }}
                    />

                  </div>

                )}

              </div>

            </div>

          );

        })}

      </div>



      {/* ========================================= */}
      {/* MAIN TOP GRID */}
      {/* ========================================= */}

      <div className="workshop-main-grid">


        {/* JOB PROGRESS */}
      <section className="dashboard-panel manpower-panel">
       {/* =====================================
    JOB PROGRESS BY STAGE
===================================== */}

<div className="dashboard-card job-progress-card">

  <div className="section-header">

    <div>

      <h3>Job Progress by Stage</h3>

      <p>
        Current jobs across workshop stages
      </p>

    </div>

  </div>


  {filteredJobProgressData.length > 0 ? (

    <div
      style={{
        width: "100%",
        height: Math.max(
          260,
          filteredJobProgressData.length * 55
        ),
      }}
    >

      <ResponsiveContainer>

        <BarChart
          layout="vertical"
          data={filteredJobProgressData}
          margin={{
            top: 10,
            right: 35,
            left: 30,
            bottom: 10,
          }}
        >

          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
          />

          <XAxis
            type="number"
            allowDecimals={false}
            axisLine={false}
            tickLine={false}
          />

          <YAxis
            type="category"
            dataKey="stage"
            width={110}
            axisLine={false}
            tickLine={false}
          />

          <Tooltip
            formatter={(value) => [
              value,
              "Jobs"
            ]}
          />

          <Bar
          dataKey="count"
          radius={[0, 6, 6, 0]}
          fill="#2563EB"
          barSize={28}
          cursor="pointer"
          onClick={handleJobProgressClick}
        />

        </BarChart>

      </ResponsiveContainer>

    </div>

  ) : (

    <div
      className="empty-chart"
      style={{
        height: 260,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >

      No job progress data available

    </div>

  )}

</div>

      </section>
        



        {/* MANPOWER */
        
        
        }
        
        <section className="dashboard-panel manpower-panel">

          <div className="panel-header">

            <h3>

              Manpower Utilization

            </h3>

          </div>


          <div className="manpower-grid">

            
            <ManpowerCard
  title="Technicians"
  data={manpowerData.technicians}
/>


            <ManpowerCard

  icon={Car}

  title="Denters"

  data={
    manpowerData.denters || {
      current: 0,
      total: 0,
      percentage: 0
    }
  }

  color="orange"

/>


            <ManpowerCard
              icon={Paintbrush}
              title="Painters"
              data={manpower.painters}
              color="purple"
            />


            <ManpowerCard
              icon={Wrench}
              title="Mechanics"
              data={manpower.mechanics}
              color="green"
            />

          </div>


          <div className="workshop-utilization">

            <div className="utilization-circle">

              <strong>82%</strong>

            </div>


            <div>

              <h4>

                Workshop Utilization

              </h4>

              <strong>

                70%

              </strong>

              <span>

                Capacity Utilized

              </span>

            </div>

          </div>

        </section>



        {/* TECHNICIAN PERFORMANCE */}

        <section className="dashboard-panel technician-panel">

          <div className="panel-header">

            <h3>

              Technician Performance

              <span>(Top 5)</span>

            </h3>


            <button className="view-all-btn">

              View All
              <ChevronRight size={16} />

            </button>

          </div>


          <div className="performance-table">

            <div className="performance-table-header">

              <span>Technician</span>
              <span>Assigned</span>
              <span>In Progress</span>
              <span>Completed</span>
              <span>Utilization</span>

            </div>


            {technicians.length > 0 ? (

              technicians.slice(0, 5).map(
                (technician, index) => (

                  <div
                    className="performance-table-row"
                    key={technician.id || index}
                  >

                    <div className="employee-name">

                      <div className="avatar">

                        {technician.name?.charAt(0)}

                      </div>

                      {technician.name}

                    </div>


                    <span>

                      {technician.total_jobs || 0}

                    </span>


                    <span>

                      {(technician.total_jobs || 0) -
                        (technician.completed_jobs || 0)}

                    </span>


                    <span>

                      {technician.completed_jobs || 0}

                    </span>


                    <span
                      className="utilization-badge"
                    >

                      {technician.efficiency || 0}%

                    </span>

                  </div>

                )

              )

            ) : (

              <div className="empty-state">

                No technician performance data available

              </div>

            )}

          </div>

        </section>


      </div>



      {/* ========================================= */}
      {/* SECOND ROW */}
      {/* ========================================= */}

      <div className="workshop-second-grid">


        {/* DENTER */}

        <PerformanceMiniTable
          title="Denter Performance"
          employees={[
            "Denter A",
            "Denter B",
            "Denter C",
            "Denter D"
          ]}
        />


        {/* PAINTER */}

        <PerformanceMiniTable
          title="Painter Performance"
          employees={[
            "Painter A",
            "Painter B",
            "Painter C",
            "Painter D"
          ]}
        />


        {/* BOTTLENECKS */}

        <section className="dashboard-panel bottleneck-panel">

          <div className="panel-header">

            <h3>

              <AlertTriangle
                size={19}
                color="#dc2626"
              />

              Bottlenecks / Alerts

            </h3>

          </div>


          <div className="alert-list">

            {alerts.map((alert, index) => {

              const Icon = alert.icon;

              return (

                <div
                  className="bottleneck-row"
                  key={index}
                >

                  <Icon
                    size={17}
                    className={`alert-icon ${alert.color}`}
                  />


                  <span>

                    {alert.title}

                  </span>


                  <strong>

                    {alert.value}

                  </strong>


                  <small>

                    Vehicles

                  </small>


                  <ChevronRight size={16} />

                </div>

              );

            })}

          </div>

        </section>


      </div>


    </div>

  );

};


export default WorkshopPerformanceTab;



// =====================================================
// MANPOWER CARD COMPONENT
// =====================================================

function ManpowerCard({
  icon: Icon,
  title,
  data = {},
  color,
}) {

  const current = data?.current ?? 0;

  const total = data?.total ?? 0;

  const percentage = data?.percentage ?? 0;


  return (

    <div className={`manpower-card ${color}`}>

      <div className="manpower-card-header">

        <div className="manpower-icon">

          {Icon && <Icon size={22} />}

        </div>

        <span>
          {title}
        </span>

      </div>


      <div className="manpower-values">

        <strong>

          {current}

        </strong>

        <span>

          / {total}

        </span>

      </div>


      <div className="manpower-progress">

        <div
          className="manpower-progress-fill"
          style={{

            width: `${percentage}%`

          }}
        />

      </div>


      <div className="manpower-percentage">

        {percentage}%

      </div>

    </div>

  );

}

// =====================================================
// MINI PERFORMANCE TABLE
// =====================================================

function PerformanceMiniTable({
  title,
  employees,
}) {

  return (

    <section className="dashboard-panel mini-performance-panel">

      <div className="panel-header">

        <h3>

          {title}

        </h3>


        <button className="view-all-btn">

          View All
          <ChevronRight size={16} />

        </button>

      </div>


      <div className="mini-table-header">

        <span>Employee</span>
        <span>Assigned</span>
        <span>Progress</span>
        <span>Completed</span>

      </div>


      {employees.map((name, index) => (

        <div
          className="mini-table-row"
          key={index}
        >

          <div className="employee-name">

            <div className="avatar">

              {name.charAt(0)}

            </div>

            {name}

          </div>


          <span>

            {6 - index}

          </span>


          <span>

            {3 - Math.min(index, 2)}

          </span>


          <span>

            {2 + (index % 2)}

          </span>

        </div>

      ))}

    </section>

  );

}