import React, { useState } from "react";

import "./AdminDashboard.css";

import OverviewTab from "./Admin/OverviewTab";
import FinancialTab from "./Admin/FinancialTab";
import WorkshopPerformanceTab from "./Admin/WorkshopPerformanceTab";
import InsuranceDashboardTab from "./Admin/InsuranceDashboardTab";
import TopPerformanceTab from "./Admin/TopPerformanceTab";
import ManagementAlertsTab from "./Admin/ManagementAlertsTab";
import {
  BellRing,
  CircleCheck,
} from "lucide-react";

// =====================================================
// ICON COMPONENT
// =====================================================

const Icon = ({ name, size = 20 }) => (
  <span
    className="material-symbols-outlined"
    style={{
      fontSize: size,
    }}
  >
    {name}
  </span>
);


// =====================================================
// TABS
// =====================================================

const DASHBOARD_TABS = [

  {
    id: "overview",
    label: "Overview Summary",
    icon: "dashboard",
  },

  {
    id: "financial",
    label: "Financial Dashboard",
    icon: "account_balance_wallet",
  },

  {
    id: "workshop",
    label: "Workshop Performance",
    icon: "engineering",
  },

  {
    id: "insurance",
    label: "Insurance Dashboard",
    icon: "verified",
  },

  {
    id: "performance",
    label: "Top Performance",
    icon: "emoji_events",
  },

  {
    id: "alerts",
    label: "Management Alerts",
    icon: "warning",
  },

];


// =====================================================
// COMPONENT
// =====================================================

export default function AdminDashboard({

  data = {},

  filters = {},

  onApplyFilters,

  branches = [],

}) {

  // ===================================================
  // ACTIVE TAB
  // ===================================================

  const [activeTab, setActiveTab] =
    useState("overview");


  // ===================================================
  // FILTER VALUES
  // ===================================================

  const {

    branch = "",

    period = "today",

    fromDate = "",

    toDate = "",

    setBranch,

    setPeriod,

    setFromDate,

    setToDate,

    loading = false,

    onReset,

  } = filters;


  // ===================================================
  // APPLY FILTER
  // ===================================================

  const handleApply = () => {

    if (onApplyFilters) {

      onApplyFilters();

    }

  };


  // ===================================================
  // RENDER ACTIVE TAB
  // ===================================================

  const renderActiveTab = () => {

    switch (activeTab) {


      // ===============================================
      // OVERVIEW
      // ===============================================

      case "overview":

        return (

          <OverviewTab
            data={data}
            loading={loading}
            onTabChange={setActiveTab}
          />

        );


      // ===============================================
      // FINANCIAL
      // ===============================================

      case "financial":

        return (

          <FinancialTab
            data={data}
          />

        );


      // ===============================================
      // WORKSHOP
      // ===============================================

      case "workshop":

        return (

          <WorkshopPerformanceTab
            data={data}
          />

        );


      // ===============================================
      // INSURANCE
      // ===============================================

      case "insurance":

        return (

          <InsuranceDashboardTab
            data={data}
          />

        );


      // ===============================================
      // TOP PERFORMANCE
      // ===============================================

      case "performance":

        return (

          <TopPerformanceTab
            data={data}
          />

        );


      // ===============================================
      // MANAGEMENT ALERTS
      // ===============================================

      case "alerts":

        return (

          <ManagementAlertsTab
      data={data}
      onNavigate={(tab) => setActiveTab(tab)}
    />

        );


      // ===============================================

      default:

        return (

          <OverviewTab
            data={data}
          />

        );

    }

  };


  // ===================================================
  // JSX
  // ===================================================

  return (

    <div className="admin-dashboard">

      {/* =============================================
          GLOBAL FILTER SECTION
      ============================================= */}

     

        <div className="dashboard-filter-bar">


          {/* =========================================
              BRANCH
          ========================================= */}

          <div className="filter-control">

            <label className="filter-label">

              <Icon
                name="account_tree"
                size={15}
              />

              Branch

            </label>


            <select

              className="dashboard-select"

              value={branch}

              onChange={(e) =>
                setBranch?.(e.target.value)
              }

            >

              <option value="">

                All Branches

              </option>


              {branches.map((item) => (

                <option
                  key={item.id}
                  value={item.id}
                >

                  {item.name}

                </option>

              ))}

            </select>

          </div>


          {/* =========================================
              PERIOD
          ========================================= */}

         <div className="filter-control">

            <label className="filter-label">

              <Icon
                name="calendar_month"
                size={15}
              />

              Period

            </label>


            <select

              className="dashboard-select"

              value={period}

              onChange={(e) =>
                setPeriod?.(e.target.value)
              }

            >

              <option value="today">

                Today

              </option>

              <option value="yesterday">

                Yesterday

              </option>

              <option value="this_week">

                This Week

              </option>

              <option value="this_month">

                This Month

              </option>

              <option value="last_month">

                Last Month

              </option>

              <option value="this_year">

                This Year

              </option>

              <option value="custom">

                Custom Date Range

              </option>

            </select>

          </div>


          {/* =========================================
              CUSTOM FROM DATE
          ========================================= */}

          {period === "custom" && (

            <div className="filter-group date-filter">

              <label className="filter-label">

                <Icon
                  name="date_range"
                  size={15}
                />

                From Date

              </label>


              <input

                type="date"

                className="dashboard-date-input"

                value={fromDate}

                onChange={(e) =>
                  setFromDate?.(e.target.value)
                }

              />

            </div>

          )}


          {/* =========================================
              CUSTOM TO DATE
          ========================================= */}

          {period === "custom" && (

            <div className="filter-group date-filter">

              <label className="filter-label">

                <Icon
                  name="event"
                  size={15}
                />

                To Date

              </label>


              <input

                type="date"

                className="dashboard-date-input"

                value={toDate}

                onChange={(e) =>
                  setToDate?.(e.target.value)
                }

              />

            </div>

          )}


          {/* =========================================
              ACTIONS
          ========================================= */}

          <div className="filter-actions">


            <button

              className="apply-filter-btn"

              onClick={handleApply}

              disabled={loading}

            >

              <Icon
                name="search"
                size={17}
              />

              {loading
                ? "Loading..."
                : "Apply"}

            </button>


            <button

              className="reset-filter-btn"

              onClick={() => onReset?.()}

              disabled={loading}

            >

              <Icon
                name="restart_alt"
                size={17}
              />

              Reset

            </button>

          </div>


        </div>

     


      {/* =============================================
          TABS
      ============================================= */}

      <div className="dashboard-tabs-container">

        <div className="dashboard-tabs">

          {DASHBOARD_TABS.map((tab) => (

            <button

              key={tab.id}

              className={`dashboard-tab ${
                activeTab === tab.id
                  ? "active"
                  : ""
              }`}

              onClick={() =>
                setActiveTab(tab.id)
              }

            >

              <Icon
                name={tab.icon}
                size={19}
              />

              <span>

                {tab.label}

              </span>

            </button>

          ))}

        </div>

      </div>


      {/* =============================================
          TAB CONTENT
      ============================================= */}

      <div className="dashboard-tab-content">

        {renderActiveTab()}

      </div>


    </div>

  );

}