import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  CalendarDays,
  Car,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Download,
  FileText,
  Filter,
  History,
  Import,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  UserRound,
  XCircle,
} from "lucide-react";

import "./JobCards.css";

/* =========================================================
   CONSTANTS
========================================================= */

const API_URL = "/api/jobcards/";

const STATUS_TABS = [
  {
    key: "all",
    label: "All",
  },
  {
    key: "progress",
    label: "In Progress",
  },
  {
    key: "completed",
    label: "Completed",
  },
  {
    key: "hold",
    label: "On Hold",
  },
];

/* =========================================================
   HELPERS
========================================================= */

const safeString = (value, fallback = "") => {
  if (value === null || value === undefined) {
    return fallback;
  }

  return String(value);
};

const normalize = (value) =>
  safeString(value)
    .trim()
    .toLowerCase();

const getJobStatus = (job) => {
  return normalize(
    job?.work_progress_status ||
      job?.repair_status ||
      ""
  );
};

const getDisplayStatus = (job) => {
  return (
    job?.work_progress_status ||
    job?.repair_status ||
    "Open"
  );
};

const isCompleted = (job) => {
  return getJobStatus(job).includes("complete");
};

const isOnHold = (job) => {
  return getJobStatus(job).includes("hold");
};

const isPending = (job) => {
  return getJobStatus(job).includes("pending");
};

const isCancelled = (job) => {
  return getJobStatus(job).includes("cancel");
};

const isInProgress = (job) => {
  const status = getJobStatus(job);

  if (!status) {
    return false;
  }

  return (
    !status.includes("complete") &&
    !status.includes("hold") &&
    !status.includes("pending") &&
    !status.includes("not started") &&
    !status.includes("not-started")
  );
};

const getStatusClass = (job) => {
  const status = getJobStatus(job);

  if (status.includes("complete")) {
    return "status-completed";
  }

  if (status.includes("hold")) {
    return "status-hold";
  }

  if (status.includes("pending")) {
    return "status-pending";
  }

  return "status-progress";
};

const getJobDate = (job) => {
  return safeString(
    job?.job_date ||
      job?.created_at ||
      ""
  ).slice(0, 10);
};

const formatDateTime = (value) => {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return safeString(value);
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getVehicleImage = (job) => {
  return (
    job?.vehicle_condition_photo ||
    "/static/images/car-top-view.png"
  );
};

/* =========================================================
   KPI CARD
========================================================= */

function KpiCard({
  icon: Icon,
  label,
  value,
  trend,
  type = "blue",
}) {
  return (
    <div className={`jc-kpi jc-kpi-${type}`}>
      <div className="jc-kpi-top">
        <div className="jc-kpi-label">
          {label}
        </div>

        <div className="jc-kpi-icon">
          <Icon size={19} strokeWidth={2.2} />
        </div>
      </div>

      <div className="jc-kpi-value">
        {value}
      </div>

      <div className="jc-kpi-trend">
        {trend}
      </div>
    </div>
  );
}

/* =========================================================
   JOB CARD ROW
========================================================= */

function JobCardRow({ job, onOpen }) {
  const vehicleModel =
    job?.claim__vehicle__model__name ||
    job?.vehicle__model__name ||
    "Vehicle";

  const registration =
    job?.claim__vehicle__registration_no ||
    job?.vehicle__registration_no ||
    "No registration";

  const customer =
    job?.claim__vehicle__customer__name ||
    job?.vehicle__customer__name ||
    "Customer";

  const insurance =
    job?.claim__insurance ||
    job?.insurance ||
    "Not specified";

  const advisor =
    job?.advisor__name ||
    "Unassigned";

  const claimNo =
    job?.claim__claim_no ||
    "Direct Job";

  const claimType =
    job?.claim__claim_type ||
    "Service";

  const stage =
    job?.claim__stage_name ||
    "No Claim";

  const intimated = Boolean(
    job?.claim__intimation_date
  );

  const displayStatus =
    getDisplayStatus(job);

  return (
    <article
      className="jc-row"
      onClick={() => onOpen(job)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (
          event.key === "Enter" ||
          event.key === " "
        ) {
          onOpen(job);
        }
      }}
    >
      {/* Vehicle */}
      <div className="jc-vehicle-cell">
        <div className="jc-vehicle-image-wrap">
          <img
            src={getVehicleImage(job)}
            alt={vehicleModel}
            className="jc-vehicle-image"
            onError={(event) => {
              event.currentTarget.src =
                "/static/images/car-top-view.png";
            }}
          />
        </div>
      </div>

      {/* Job Details */}
      <div className="jc-details-cell">
        <div className="jc-job-number">
          {job?.job_no || "—"}
        </div>

        <div className="jc-model">
          {vehicleModel}
        </div>

        {/* Claim */}
        <div className="jc-claim-row">
          <span className="jc-claim-main">
            Claim: {claimNo}
          </span>

          <span className="jc-dot" />

          <span>
            {claimType}
          </span>

          <span className="jc-stage">
            Stage: {stage}
          </span>

          <span
            className={
              intimated
                ? "jc-intimated"
                : "jc-not-intimated"
            }
          >
            {intimated
              ? "Intimated"
              : "Intimation Pending"}
          </span>
        </div>

        {/* Vehicle Meta */}
        <div className="jc-meta-row">
          <span>
            <Car size={13} />
            {registration}
          </span>

          <span>
            <UserRound size={13} />
            {customer}
          </span>

          <span>
            <ShieldCheck size={13} />
            {insurance}
          </span>
        </div>

        {/* Footer */}
        <div className="jc-footer">
          <span>
            <Clock3 size={13} />
            {formatDateTime(
              job?.created_at
            )}
          </span>

          <span>
            <UserRound size={13} />
            {advisor}
          </span>
        </div>
      </div>

      {/* Status */}
      <div className="jc-status-cell">
        <span
          className={`jc-status ${getStatusClass(
            job
          )}`}
        >
          {displayStatus}
        </span>
      </div>

      {/* Action */}
      <div className="jc-action-cell">
        <button
          type="button"
          className="jc-open-button"
          onClick={(event) => {
            event.stopPropagation();
            onOpen(job);
          }}
          aria-label={`Open job ${
            job?.job_no || ""
          }`}
        >
          <ArrowRight size={20} />
        </button>
      </div>
    </article>
  );
}

/* =========================================================
   EMPTY STATE
========================================================= */

function EmptyState({ searchActive }) {
  return (
    <div className="jc-empty">
      <div className="jc-empty-icon">
        <FileText size={27} />
      </div>

      <h3>
        No job cards found
      </h3>

      <p>
        {searchActive
          ? "Try changing your search or filters."
          : "There are no job cards available."}
      </p>
    </div>
  );
}

/* =========================================================
   LOADING STATE
========================================================= */

function LoadingState() {
  return (
    <div className="jc-loading">
      <RefreshCw
        size={22}
        className="jc-spin"
      />

      <span>
        Loading job cards...
      </span>
    </div>
  );
}

/* =========================================================
   ERROR STATE
========================================================= */

function ErrorState({ message, onRetry }) {
  return (
    <div className="jc-error">
      <div className="jc-error-icon">
        <AlertCircle size={23} />
      </div>

      <div className="jc-error-content">
        <strong>
          Unable to load job cards
        </strong>

        <span>
          {message ||
            "Please try again."}
        </span>
      </div>

      <button
        type="button"
        className="jc-retry-button"
        onClick={onRetry}
      >
        <RefreshCw size={15} />
        Retry
      </button>
    </div>
  );
}

/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function JobCards() {
  const [jobs, setJobs] = useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [search, setSearch] =
    useState("");

  const [activeTab, setActiveTab] =
    useState("all");

  const [branch, setBranch] =
    useState("");

  const [advisor, setAdvisor] =
    useState("");

  const [serviceType, setServiceType] =
    useState("");

  const [dateFrom, setDateFrom] =
    useState("");

  const [dateTo, setDateTo] =
    useState("");

  /* =======================================================
     LOAD JOB CARDS
  ======================================================= */

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        API_URL,
        {
          headers: {
            Accept:
              "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Server returned ${response.status}`
        );
      }

      const data =
        await response.json();

      if (Array.isArray(data)) {
        setJobs(data);
      } else if (
        Array.isArray(data?.results)
      ) {
        setJobs(data.results);
      } else {
        setJobs([]);
      }
    } catch (err) {
      console.error(
        "Job Cards API Error:",
        err
      );

      setError(
        err?.message ||
          "Unable to load job cards."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  /* =======================================================
     FILTER OPTIONS
  ======================================================= */

  const branches = useMemo(() => {
    const map = new Map();

    jobs.forEach((job) => {
      if (job?.branch__id) {
        map.set(
          String(job.branch__id),
          job.branch__name ||
            `Branch ${job.branch__id}`
        );
      }
    });

    return Array.from(
      map.entries()
    );
  }, [jobs]);

  const advisors = useMemo(() => {
    const map = new Map();

    jobs.forEach((job) => {
      if (job?.advisor__id) {
        map.set(
          String(job.advisor__id),
          job.advisor__name ||
            `Advisor ${job.advisor__id}`
        );
      }
    });

    return Array.from(
      map.entries()
    );
  }, [jobs]);

  const serviceTypes = useMemo(() => {
    return [
      ...new Set(
        jobs
          .map(
            (job) =>
              job?.service_type
          )
          .filter(Boolean)
      ),
    ];
  }, [jobs]);

  /* =======================================================
     TAB FILTER
  ======================================================= */

  const matchesTab = (job) => {
    if (activeTab === "all") {
      return true;
    }

    if (activeTab === "completed") {
      return isCompleted(job);
    }

    if (activeTab === "hold") {
      return isOnHold(job);
    }

    if (activeTab === "progress") {
      return isInProgress(job);
    }

    return true;
  };

  /* =======================================================
     FILTERED JOBS
  ======================================================= */

  const filteredJobs = useMemo(() => {
    const query =
      normalize(search);

    return jobs.filter((job) => {
      const jobDate =
        getJobDate(job);

      const matchesSearch =
        !query ||
        JSON.stringify(job)
          .toLowerCase()
          .includes(query);

      const matchesBranch =
        !branch ||
        String(
          job?.branch__id || ""
        ) === branch;

      const matchesAdvisor =
        !advisor ||
        String(
          job?.advisor__id || ""
        ) === advisor;

      const matchesService =
        !serviceType ||
        job?.service_type ===
          serviceType;

      const matchesFrom =
        !dateFrom ||
        jobDate >= dateFrom;

      const matchesTo =
        !dateTo ||
        jobDate <= dateTo;

      return (
        matchesTab(job) &&
        matchesSearch &&
        matchesBranch &&
        matchesAdvisor &&
        matchesService &&
        matchesFrom &&
        matchesTo
      );
    });
  }, [
    jobs,
    search,
    activeTab,
    branch,
    advisor,
    serviceType,
    dateFrom,
    dateTo,
  ]);

  /* =======================================================
     KPIs
  ======================================================= */

  const kpis = useMemo(() => {
    return {
      total: jobs.length,

      progress: jobs.filter(
        isInProgress
      ).length,

      completed: jobs.filter(
        isCompleted
      ).length,

      pending: jobs.filter(
        isPending
      ).length,

      cancelled: jobs.filter(
        isCancelled
      ).length,
    };
  }, [jobs]);

  /* =======================================================
     TAB COUNTS
  ======================================================= */

  const tabCounts = useMemo(() => {
    return {
      all: jobs.length,

      progress: jobs.filter(
        isInProgress
      ).length,

      completed: jobs.filter(
        isCompleted
      ).length,

      hold: jobs.filter(
        isOnHold
      ).length,
    };
  }, [jobs]);

  /* =======================================================
     OPEN JOB
  ======================================================= */

  const handleOpenJob = (job) => {
    if (!job?.id) {
      return;
    }

    window.location.href =
      `/jobCard/${job.id}/edit/`;
  };

  /* =======================================================
     CLEAR FILTERS
  ======================================================= */

  const clearFilters = () => {
    setSearch("");
    setBranch("");
    setAdvisor("");
    setServiceType("");
    setDateFrom("");
    setDateTo("");
    setActiveTab("all");
  };

  const hasFilters =
    Boolean(search) ||
    Boolean(branch) ||
    Boolean(advisor) ||
    Boolean(serviceType) ||
    Boolean(dateFrom) ||
    Boolean(dateTo) ||
    activeTab !== "all";

  /* =======================================================
     EXPORT
  ======================================================= */

  const handleExport = () => {
    /*
      Your old Django page points Export to:
      part_order_list

      Keep this URL if that is still your
      existing Django export endpoint.
    */

    window.location.href =
      "/part-order-list/";
  };

  /* =======================================================
     IMPORT
  ======================================================= */

  const handleImport = () => {
    /*
      Import was only a button in the
      original Django page.

      No import endpoint was provided
      in the uploaded HTML, so we don't
      invent one here.
    */

    console.info(
      "Import button clicked."
    );
  };

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="job-cards-page">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="jc-header">
        <div className="jc-header-left">
          <div className="jc-breadcrumb">
            <span>Dashboard</span>
            <ChevronDown size={12} />
            <strong>
              Job Cards
            </strong>
          </div>

          <div className="jc-heading-row">
            <div>
              <h1>
                Job Cards
              </h1>

              <p>
                Manage and track all
                workshop job cards
              </p>
            </div>
          </div>
        </div>

        <div className="jc-header-actions">

          <button
            type="button"
            className="jc-button jc-button-secondary"
            onClick={handleExport}
          >
            <Download size={16} />
            Export
          </button>

          <button
            type="button"
            className="jc-button jc-button-secondary"
            onClick={handleImport}
          >
            <Import size={16} />
            Import
          </button>

          <button
            type="button"
            className="jc-button jc-button-primary"
            onClick={() => {
              window.location.href =
                "/jobCreate/";
            }}
          >
            <Plus size={17} />
            New Job Card
          </button>

        </div>
      </header>

      {/* =================================================
          KPI CARDS
      ================================================= */}

      <section className="jc-kpis">

        <KpiCard
          icon={FileText}
          label="Total Job Cards"
          value={kpis.total}
          trend="Current job cards"
          type="blue"
        />

        <KpiCard
          icon={Activity}
          label="In Progress"
          value={kpis.progress}
          trend="Currently in workshop"
          type="green"
        />

        <KpiCard
          icon={CheckCircle2}
          label="Completed"
          value={kpis.completed}
          trend="Work completed"
          type="orange"
        />

        <KpiCard
          icon={Clock3}
          label="Pending Approval"
          value={kpis.pending}
          trend="Awaiting action"
          type="purple"
        />

        <KpiCard
          icon={XCircle}
          label="Cancelled"
          value={kpis.cancelled}
          trend="Cancelled job cards"
          type="red"
        />

      </section>

      {/* =================================================
          TABS
      ================================================= */}

      <section className="jc-panel">

        <div className="jc-tabs">

          {STATUS_TABS.map(
            (tab) => (
              <button
                key={tab.key}
                type="button"
                className={`jc-tab ${
                  activeTab === tab.key
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setActiveTab(
                    tab.key
                  )
                }
              >
                <span>
                  {tab.label}
                </span>

                <span className="jc-count">
                  {
                    tabCounts[
                      tab.key
                    ]
                  }
                </span>
              </button>
            )
          )}

        </div>

        {/* ===============================================
            FILTER BAR
        =============================================== */}

        <div className="jc-filter-bar">

          {/* Search */}

          <div className="jc-search-box">
            <Search
              size={17}
              className="jc-search-icon"
            />

            <input
              type="text"
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search by Job No, Vehicle, Customer..."
            />

            {search && (
              <button
                type="button"
                className="jc-search-clear"
                onClick={() =>
                  setSearch("")
                }
              >
                ×
              </button>
            )}
          </div>

          {/* Branch */}

          <div className="jc-select-wrap">
            <select
              value={branch}
              onChange={(event) =>
                setBranch(
                  event.target.value
                )
              }
            >
              <option value="">
                All Branches
              </option>

              {branches.map(
                ([value, label]) => (
                  <option
                    key={value}
                    value={value}
                  >
                    {label}
                  </option>
                )
              )}
            </select>

            <ChevronDown
              size={15}
            />
          </div>

          {/* Advisor */}

          <div className="jc-select-wrap">
            <select
              value={advisor}
              onChange={(event) =>
                setAdvisor(
                  event.target.value
                )
              }
            >
              <option value="">
                All Advisors
              </option>

              {advisors.map(
                ([value, label]) => (
                  <option
                    key={value}
                    value={value}
                  >
                    {label}
                  </option>
                )
              )}
            </select>

            <ChevronDown
              size={15}
            />
          </div>

          {/* Service */}

          <div className="jc-select-wrap">
            <select
              value={serviceType}
              onChange={(event) =>
                setServiceType(
                  event.target.value
                )
              }
            >
              <option value="">
                All Service Types
              </option>

              {serviceTypes.map(
                (type) => (
                  <option
                    key={type}
                    value={type}
                  >
                    {type}
                  </option>
                )
              )}
            </select>

            <ChevronDown
              size={15}
            />
          </div>

          {/* Date From */}

          <div className="jc-date-box">
            <CalendarDays size={15} />

            <input
              type="date"
              value={dateFrom}
              onChange={(event) =>
                setDateFrom(
                  event.target.value
                )
              }
            />
          </div>

          {/* Date To */}

          <div className="jc-date-box">
            <CalendarDays size={15} />

            <input
              type="date"
              value={dateTo}
              onChange={(event) =>
                setDateTo(
                  event.target.value
                )
              }
            />
          </div>

          {/* Filter Button */}

          <button
            type="button"
            className="jc-filter-button"
            onClick={loadJobs}
            title="Refresh job cards"
          >
            <RefreshCw size={16} />
            Refresh
          </button>

        </div>

        {/* Active filters */}

        {hasFilters && (
          <div className="jc-active-filter-bar">

            <div className="jc-active-filter-label">
              <Filter size={14} />
              Filters active
            </div>

            <button
              type="button"
              onClick={clearFilters}
              className="jc-clear-filters"
            >
              Clear all
            </button>

          </div>
        )}

      </section>

      {/* =================================================
          LIST
      ================================================= */}

      <section className="jc-list-container">

        {/* List Header */}

        <div className="jc-list-header">
          <div>
            Vehicle
          </div>

          <div>
            Job Card Details
          </div>

          <div>
            Status
          </div>

          <div>
            Action
          </div>
        </div>

        {/* List */}

        <div className="jc-list">

          {loading && (
            <LoadingState />
          )}

          {!loading && error && (
            <ErrorState
              message={error}
              onRetry={loadJobs}
            />
          )}

          {!loading &&
            !error &&
            filteredJobs.length ===
              0 && (
              <EmptyState
                searchActive={
                  hasFilters
                }
              />
            )}

          {!loading &&
            !error &&
            filteredJobs.length >
              0 &&
            filteredJobs.map(
              (job) => (
                <JobCardRow
                  key={job.id}
                  job={job}
                  onOpen={
                    handleOpenJob
                  }
                />
              )
            )}

        </div>

        {/* Result footer */}

        {!loading &&
          !error &&
          filteredJobs.length >
            0 && (
            <div className="jc-list-footer">

              <div>
                Showing{" "}
                <strong>
                  {filteredJobs.length}
                </strong>{" "}
                of{" "}
                <strong>
                  {jobs.length}
                </strong>{" "}
                job cards
              </div>

              <div className="jc-last-refresh">
                <History size={14} />
                Data from Job Card API
              </div>

            </div>
          )}

      </section>

    </div>
  );
}