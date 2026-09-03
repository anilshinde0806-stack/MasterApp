import { useEffect, useState } from "react";

import "./Dashboard.css";

import AdminDashboard from "./AdminDashboard";
import AdvisorDashboard from "./AdvisorDashboard";


export default function Dashboard() {


  // ==========================================
  // STATE
  // ==========================================

  const [dashboardType, setDashboardType] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [data, setData] =
    useState({});

  const [branches, setBranches] =
    useState([]);


  // ==========================================
  // FILTERS
  // ==========================================

  const [filters, setFilters] = useState({

    branch: "",
    period: "today",
    from_date: "",
    to_date: "",

  });


  // ==========================================
  // LOAD BRANCHES
  // ==========================================

  useEffect(() => {

    async function loadBranches() {

      try {

        const response = await fetch(

          "/ajax/dashboard-branches/",

          {
            credentials: "same-origin"
          }

        );


        if (!response.ok) {

          throw new Error(
            "Unable to load branches."
          );

        }


        const result =
          await response.json();


        setBranches(
          result.branches || []
        );


      } catch (error) {

        console.error(
          "Branch API error:",
          error
        );

      }

    }


    loadBranches();

  }, []);


  // ==========================================
  // LOAD DASHBOARD
  // ==========================================

  async function loadDashboard(
    activeFilters = filters
  ) {

    try {

      setLoading(true);

      setError("");


      const params =
        new URLSearchParams();


      // ======================================
      // BRANCH
      // ======================================

      if (activeFilters.branch) {

        params.append(

          "branch",

          activeFilters.branch

        );

      }


      // ======================================
    // PERIOD
    // ======================================

    if (activeFilters.period) {

      params.append(
        "period",
         activeFilters.period || "today"
      );

    }


    // ======================================
    // CUSTOM DATES
    // Only send when period is custom
    // ======================================
    console.log(
        "period:",
        activeFilters.period
      );
    if (activeFilters.period === "custom") {
       console.log(
        "fromDate:",
        activeFilters.from_date
      );
      if (activeFilters.from_date) {

        params.append(
          "start_date",
          activeFilters.from_date
        );

      }


      if (activeFilters.to_date) {

        params.append(
          "end_date",
          activeFilters.to_date
        );

      }

    }



      // ======================================
      // API URL
      // ======================================

      const queryString =
        params.toString();


      const url =
        `/api/mobile/newdashboard/${
          queryString
            ? `?${queryString}`
            : ""
        }`;


      console.log(
        "Dashboard URL:",
        url
      );


      // ======================================
      // FETCH API
      // ======================================

      const response =
        await fetch(

          url,

          {
            credentials: "same-origin"
          }

        );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );

      }


      const result =
        await response.json();


      console.log(
        "DASHBOARD API:",
        result
      );


      // ======================================
      // DASHBOARD TYPE
      // ======================================

      setDashboardType(

        (
          result.dashboard_type ||
          "ADMIN"
        ).toUpperCase()

      );


      // ======================================
      // NORMALIZED DATA
      //
      // Keep API structure intact.
      // ======================================

      const normalizedData = {

        ...result,


        // ====================================
        // OVERVIEW COMPATIBILITY VALUES
        // ====================================

        active_claims:

          result?.summaries?.find(

            item =>
              item.type === "claims"

          )?.value ?? 0,


        active_job_cards:

          result?.summaries?.find(

            item =>
              item.type === "jobcards"

          )?.value ?? 0,


        vehicles_in_workshop:

          result?.summaries?.find(

            item =>
              item.type === "workshop"

          )?.value ?? 0,


        pending_delivery:

          result?.summaries?.find(

            item =>
              item.type === "delivery"

          )?.value ?? 0,


        // ====================================
        // REVENUE
        // ====================================

        revenue: {

          total:

            Number(
              result?.revenue?.total || 0
            ),


          parts:

            Number(
              result?.revenue?.parts || 0
            ),


          labour:

            Number(
              result?.revenue?.labour || 0
            ),


          trend:

            result?.revenue?.trend || []

        },


        // ====================================
        // OLD REVENUE TREND FORMAT
        //
        // Kept only for compatibility.
        // ====================================

        revenue_trend:

          (
            result?.revenue?.trend || []
          ).map(

            item => ({

              month:

                item.label ||
                item.month ||
                item.date,


              revenue:

                Number(

                  item.total ??
                  item.revenue ??
                  0

                )

            })

          ),


        // ====================================
        // PIPELINE
        // ====================================

        pipeline:

          result?.pipeline || [],


        // ====================================
        // PERFORMANCE
        // ====================================

        performance:

          result?.performance || {

            total_jobs: 0,

            completed_jobs: 0,

            pending_jobs: 0,

            running_jobs: 0,

            completion_percentage: 0,

            average_tat: "0"

          },


        // ====================================
        // FINANCIAL
        // ====================================

        financial:

          result?.financial || {},


        // ====================================
        // TOP ADVISORS
        // ====================================

        top_advisors:

          result?.top_advisors || [],


        // ====================================
        // TOP TECHNICIANS
        // ====================================

        top_technicians:

          result?.top_technicians || [],


        // ====================================
        // BRANCH PERFORMANCE
        // ====================================

        branch_performance:

          result?.branch_performance || []

      };


      console.log(
        "NORMALIZED DATA:",
        normalizedData
      );


      // ======================================
      // STORE DATA
      // ======================================

      setData(
        normalizedData
      );


    } catch (err) {

      console.error(
        "Dashboard API error:",
        err
      );


      setError(

        err.message ||
        "Unable to load dashboard data."

      );


    } finally {

      setLoading(false);

    }

  }


  // ==========================================
  // INITIAL LOAD
  // ==========================================

  useEffect(() => {

    loadDashboard({

      branch: "",

      from_date: "",

      to_date: ""

    });

  }, []);


  // ==========================================
  // FILTER FUNCTIONS
  // ==========================================

 
const setBranch = (value) => {

  setFilters((prev) => ({
    ...prev,
    branch: value
  }));

};
const setFromDate = (value) => {

  console.log("Setting From Date:", value);

  setFilters((prev) => ({
    ...prev,
    from_date: value,
  }));

};


const setToDate = (value) => {

  console.log("Setting To Date:", value);

  setFilters((prev) => ({
    ...prev,
    to_date: value,
  }));

};

const setPeriod = (value) => {

  setFilters((prev) => ({
    ...prev,

    period: value,

    from_date:
      value === "custom"
        ? prev.from_date
        : "",

    to_date:
      value === "custom"
        ? prev.to_date
        : ""

  }));

};




  


  // ==========================================
  // APPLY FILTERS
  // ==========================================

 const handleApplyFilters = () => {

  if (filters.period === "custom") {

    if (!filters.from_date || !filters.to_date) {

      alert("Please select both From Date and To Date.");

      return;

    }

  }

  loadDashboard(filters);

};


  // ==========================================
  // RESET FILTERS
  // ==========================================

  function handleResetFilters() {

    const resetFilters = {

      branch: "",

      from_date: "",

      to_date: ""

    };


    setFilters(
      resetFilters
    );


    loadDashboard(
      resetFilters
    );

  }


  // ==========================================
  // FILTER PROPS
  // ==========================================

const filterProps = {

  // =====================================
  // BRANCH
  // =====================================

  branch:
    filters.branch || "",

  setBranch,


  // =====================================
  // PERIOD
  // =====================================

  period:
    filters.period || "today",

  setPeriod,


  // =====================================
  // CUSTOM DATE RANGE
  // =====================================

  fromDate:
    filters.from_date || "",

  toDate:
    filters.to_date || "",

  setFromDate,

  setToDate,


  // =====================================
  // LOADING
  // =====================================

  loading,


  // =====================================
  // RESET
  // =====================================

  onReset:
    handleResetFilters

};
console.log(
  "FILTER PROPS:",
  filterProps
);
  // ==========================================
  // LOADING
  // ==========================================

  if (loading && !dashboardType) {

    return (

      <div className="dashboard-loading">

        <i className="fa-solid fa-spinner fa-spin"></i>

        Loading dashboard...

      </div>

    );

  }


  // ==========================================
  // ERROR
  // ==========================================

  if (error) {

    return (

      <div className="dashboard-error">

        <i className="fa-solid fa-circle-exclamation"></i>

        {error}

      </div>

    );

  }


  // ==========================================
  // ADVISOR DASHBOARD
  // ==========================================

  if (dashboardType === "ADVISOR") {

    return (

      <AdvisorDashboard

        data={data}

        filters={filterProps}

        onApplyFilters={
          handleApplyFilters
        }

        branches={branches}

      />

    );

  }


  // ==========================================
  // ADMIN DASHBOARD
  // ==========================================

  return (

    <AdminDashboard

      data={data}

      filters={filterProps}

      onApplyFilters={
        handleApplyFilters
      }

      branches={branches}

    />

  );

}