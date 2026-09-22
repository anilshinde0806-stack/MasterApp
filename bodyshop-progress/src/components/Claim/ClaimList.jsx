import React, { useEffect, useMemo, useState } from "react";
import {
  Menu,
  Car,
  Home,
  ClipboardList,
  ShieldCheck,
  BarChart3,
  Settings,
  MapPin,
  Bell,
  UserCircle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  RotateCcw,
  Download,
  Columns3,
  Pencil,
  FileText,
  CheckCircle2,
  Clock3,
  AlertTriangle,
  X,
  ArrowUpDown,
  CircleCheck,
} from "lucide-react";

import "./ClaimList.css";

const localDateISO = (date) => { const year = date.getFullYear(); const month = String(date.getMonth() + 1).padStart(2, "0"); const day = String(date.getDate()).padStart(2, "0"); return `${year}-${month}-${day}`; };
const todayISO = () => localDateISO(new Date());
const monthStartISO = () => { const date = new Date(); return localDateISO(new Date(date.getFullYear(), date.getMonth(), 1)); };





/* ============================================================
   STAGE CONFIGURATION
   ============================================================ */

const STAGE_CLASS = {
  "Repair Work In Progress": "repair",
  "Work Allocation Pending": "work-allocation",
  "Claim Intimation Pending": "intimation",
  "Insurance Approval": "approval",
  Liability: "liability",
  "Claim Intimation": "intimation",
  "Advisor Assigned": "advisor",
};


/* ============================================================
   HELPERS
   ============================================================ */

function formatDateTime(value) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}


function formatDate(value) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("en-IN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}


function getDaysClass(days) {
  if (days >= 30) {
    return "danger";
  }

  if (days >= 15) {
    return "warning";
  }

  return "normal";
}


/* ============================================================
   MAIN COMPONENT
   ============================================================ */

export default function ClaimList() {
  const scopeFilters = window.__CLAIM_LIST_FILTERS__ || null;
  const [claimData, setClaimData] = useState([]);
  const [claimSummary, setClaimSummary] = useState({ total: 0, in_progress: 0, pending: 0, overdue: 0 });
  const CLAIM_DATA = claimData;
  useEffect(() => {
    fetch("/api/claim/?format=react&claim_status=all", { credentials: "same-origin" })
      .then((response) => response.json())
      .then((payload) => {
        const rows = (payload.data || []).map((item) => ({ ...item, claimNo: item.claim_no, regNo: item.vehicle__registration_no, customer: item.vehicle__customer__name, mobile: item.vehicle__customer__mobile_no, model: item.vehicle__model__name, advisor: item.employee__name, createdDate: item.created_at, insuranceCompany: item.insurance_company__ins_co_name, icClaimNo: item.ic_claim_no, accidentDate: item.accident_date, intimationDate: item.intimation_date, daysSinceIntimation: item.intimation_date ? Math.max(0, Math.floor((Date.now() - new Date(item.intimation_date).getTime()) / 86400000)) : 0, stage: item.claim_stage_name, stageType: item.claim_stage_name }));
        setClaimData(rows); setClaimSummary(payload.summary || {});
      });
  }, []);

  /* ----------------------------------------------------------
     FILTER STATE
     ---------------------------------------------------------- */

  const [filters, setFilters] = useState({
    fromDate: monthStartISO(),
    toDate: todayISO(),
    advisorStatus: "All",
    claimStatus: "Open",
    branch: "",
    advisorName: window.__CLAIM_LIST_CURRENT_ADVISOR__?.name || "",
    claimType: "",
    search: "",
  });


  const [appliedFilters, setAppliedFilters] = useState(filters);

  const [currentPage, setCurrentPage] = useState(1);

  const [pageSize] = useState(8);

  const [selectedClaims, setSelectedClaims] = useState([]);

  const [sortField, setSortField] = useState("createdDate");

  const [sortDirection, setSortDirection] = useState("desc");


  /* ----------------------------------------------------------
     FILTER HANDLER
     ---------------------------------------------------------- */

  const handleFilterChange = (event) => {
    const { name, value } = event.target;

    setFilters((previous) => ({
      ...previous,
      [name]: value,
    }));
  };


  /* ----------------------------------------------------------
     APPLY FILTER
     ---------------------------------------------------------- */

  const handleApplyFilter = () => {
    setAppliedFilters(filters);
    setCurrentPage(1);
  };


  /* ----------------------------------------------------------
     RESET FILTER
     ---------------------------------------------------------- */

  const handleReset = () => {

    const resetFilters = {
      fromDate: monthStartISO(),
      toDate: todayISO(),
      advisorStatus: "All",
      claimStatus: "Open",
      branch: "",
      advisorName: window.__CLAIM_LIST_CURRENT_ADVISOR__?.name || "",
      claimType: "",
      search: "",
    };

    setFilters(resetFilters);
    setAppliedFilters(resetFilters);
    setCurrentPage(1);
  };


  /* ----------------------------------------------------------
     SEARCH + FILTER + SORT
     ---------------------------------------------------------- */

  const filteredClaims = useMemo(() => {

    let result = [...CLAIM_DATA];

    const {
      fromDate,
      toDate,
      advisorStatus,
      claimStatus,
      advisorName,
      claimType,
      branch,
      search,
    } = appliedFilters;


    /* Search */

    if (branch) result = result.filter((claim) => String(claim.branch_id || claim.branch || "") === String(branch));

    if (search.trim()) {

      const query = search.toLowerCase().trim();

      result = result.filter((claim) =>
        [
          claim.claimNo,
          claim.regNo,
          claim.customer,
          claim.mobile,
          claim.model,
          claim.advisor,
          claim.insuranceCompany,
          claim.icClaimNo,
        ]
          .filter(Boolean)
          .some((value) =>
            String(value)
              .toLowerCase()
              .includes(query)
          )
      );
    }


    /* Advisor */

    if (advisorName) {

      result = result.filter(
        (claim) =>
          claim.advisor === advisorName
      );
    }


    /* Advisor Status */

    if (
      advisorStatus &&
      advisorStatus !== "All"
    ) {

      result = result.filter(
        (claim) =>
          advisorStatus === "Assigned"
            ? Boolean(claim.advisor)
            : !claim.advisor
      );
    }


    /* Claim Status */

    if (claimStatus === "Open") {

      result = result.filter(
        (claim) =>
          claim.stage !== "Delivery" &&
          claim.stage !== "Closed"
      );
    }


    if (claimStatus === "Closed") {

      result = result.filter(
        (claim) =>
          claim.stage === "Closed"
      );
    }


    /* Date */

    if (fromDate) {

      result = result.filter(
        (claim) =>
          new Date(claim.createdDate) >=
          new Date(fromDate)
      );
    }


    if (toDate) {

      const endDate = new Date(toDate);

      endDate.setHours(
        23,
        59,
        59,
        999
      );

      result = result.filter(
        (claim) =>
          new Date(claim.createdDate) <=
          endDate
      );
    }


    /* Sorting */

    result.sort((a, b) => {

      let first = a[sortField];
      let second = b[sortField];

      if (sortField === "createdDate") {

        first = new Date(first).getTime();
        second = new Date(second).getTime();
      }

      if (
        typeof first === "string" &&
        typeof second === "string"
      ) {

        first = first.toLowerCase();
        second = second.toLowerCase();
      }

      if (first < second) {
        return sortDirection === "asc"
          ? -1
          : 1;
      }

      if (first > second) {
        return sortDirection === "asc"
          ? 1
          : -1;
      }

      return 0;
    });

    return result;

  }, [
    appliedFilters,
    sortField,
    sortDirection,
  ]);


  /* ----------------------------------------------------------
     PAGINATION
     ---------------------------------------------------------- */

  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredClaims.length / pageSize
    )
  );


  const paginatedClaims = filteredClaims.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );


  /* ----------------------------------------------------------
     SORT
     ---------------------------------------------------------- */

  const handleSort = (field) => {

    if (sortField === field) {

      setSortDirection(
        (previous) =>
          previous === "asc"
            ? "desc"
            : "asc"
      );

    } else {

      setSortField(field);
      setSortDirection("asc");
    }
  };


  /* ----------------------------------------------------------
     SELECT ALL
     ---------------------------------------------------------- */

  const handleSelectAll = (event) => {

    if (event.target.checked) {

      setSelectedClaims(
        paginatedClaims.map(
          (claim) => claim.id
        )
      );

    } else {

      setSelectedClaims([]);
    }
  };


  /* ----------------------------------------------------------
     SELECT ONE
     ---------------------------------------------------------- */

  const handleSelectClaim = (id) => {

    setSelectedClaims((previous) => {

      if (previous.includes(id)) {

        return previous.filter(
          (claimId) =>
            claimId !== id
        );
      }

      return [
        ...previous,
        id,
      ];
    });
  };


  /* ----------------------------------------------------------
     EDIT CLAIM
     ---------------------------------------------------------- */

  const handleEditClaim = (claim) => {
    window.location.href =
  `/claim/${claim.id}/edit/`;
  };
 const handleEditjobCard = (claim) => {
    window.location.href = claim.jobcard_id
      ? `/jobCard/${claim.jobcard_id}/edit/`
      : `/claim/${claim.id}/edit/`;
  };

  /* ----------------------------------------------------------
     EXPORT
     ---------------------------------------------------------- */

  const handleExport = () => {

    const headers = [
      "Claim No",
      "Registration No",
      "Customer",
      "Mobile",
      "Model",
      "Advisor",
      "Created Date",
      "Insurance Company",
      "IC Claim No",
      "Accident Date",
      "Intimation Date",
      "Days Since Intimation",
      "Stage",
    ];

    const rows = filteredClaims.map(
      (claim) => [
        claim.claimNo,
        claim.regNo,
        claim.customer,
        claim.mobile,
        claim.model,
        claim.advisor,
        claim.createdDate,
        claim.insuranceCompany,
        claim.icClaimNo,
        claim.accidentDate,
        claim.intimationDate,
        claim.daysSinceIntimation,
        claim.stage,
      ]
    );

    const csv = [
      headers,
      ...rows,
    ]
      .map((row) =>
        row
          .map((value) =>
            `"${String(value ?? "")
              .replace(/"/g, '""')}"`
          )
          .join(",")
      )
      .join("\n");

    const blob = new Blob(
      [csv],
      {
        type: "text/csv;charset=utf-8;",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = url;

    link.download =
      "claim-list.csv";

    link.click();

    URL.revokeObjectURL(url);
  };


  /* ----------------------------------------------------------
     SUMMARY
     ---------------------------------------------------------- */

  const totalClaims = filteredClaims.length;

  const inProgressClaims = filteredClaims.filter((claim) => claim.stage !== "Closed").length;

  const pendingClaims = filteredClaims.filter((claim) => !claim.advisor).length;

  const overdueClaims = filteredClaims.filter((claim) => Number(claim.daysSinceIntimation || 0) >= 30).length;


  /* ==========================================================
     RENDER
     ========================================================== */

  return (

    <div className="claim-list-page">

      {/* ======================================================
          PAGE HEADER
          ====================================================== */}

      <section className="claim-list-header">

        <div className="claim-list-heading">

          <div className="claim-list-heading-icon">
            <FileText size={25} />
          </div>

          <div>

            <h1>
              Claim List
            </h1>

            <p>
              View and manage all insurance claims
              with their current status.
            </p>

          </div>

        </div>


        {/* SUMMARY CARDS */}

        <div className="claim-summary">

          <SummaryCard
            type="blue"
            icon={<FileText size={19} />}
            label="Total Claims"
            value={totalClaims}
          />

          <SummaryCard
            type="green"
            icon={<CheckCircle2 size={19} />}
            label="In Progress"
            value={inProgressClaims}
          />

          <SummaryCard
            type="orange"
            icon={<Clock3 size={19} />}
            label="Pending"
            value={pendingClaims}
          />

          <SummaryCard
            type="red"
            icon={<AlertTriangle size={19} />}
            label="Overdue"
            value={overdueClaims}
          />

        </div>

      </section>


      {/* ======================================================
          FILTER SECTION
          ====================================================== */}

      <section className="claim-filter-card">

        <div className="claim-filter-title">

          <Filter size={17} />

          <span>
            Search & Filter
          </span>

        </div>


        <div className="claim-filter-grid">

          {/* From Date */}

          <FilterField label="From Date">

            <input
              type="date"
              name="fromDate"
              value={filters.fromDate}
              onChange={handleFilterChange}
              className="claim-filter-input"
            />

          </FilterField>


          {/* To Date */}

          <FilterField label="To Date">

            <input
              type="date"
              name="toDate"
              value={filters.toDate}
              onChange={handleFilterChange}
              className="claim-filter-input"
            />

          </FilterField>


          {/* Advisor Status */console.log("scopeFilters:", scopeFilters)}
          
          
          
          {scopeFilters && <FilterField label="Branch"><select name="branch" value={filters.branch} onChange={handleFilterChange} className="claim-filter-select"><option value="">All Branches</option>{(scopeFilters.branches || []).map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></FilterField>}

          <FilterField label="Advisor Status">

            <select
              name="advisorStatus"
              value={filters.advisorStatus}
              onChange={handleFilterChange}
              className="claim-filter-select"
            >

              <option value="All">
                All
              </option>

              <option value="Assigned">
                Assigned
              </option>

              <option value="Unassigned">
                Unassigned
              </option>

            </select>

          </FilterField>


          {/* Claim Status */}

          <FilterField label="Claim Status">

            <select
              name="claimStatus"
              value={filters.claimStatus}
              onChange={handleFilterChange}
              className="claim-filter-select"
            >

              <option value="Open">
                Open
              </option>

              <option value="Closed">
                Closed
              </option>

              <option value="All">
                All
              </option>

            </select>

          </FilterField>


          {/* Advisor */}

          <FilterField label="Advisor Name">

              <select
                name="advisorName"
                value={filters.advisorName}
                onChange={handleFilterChange}
                className="claim-filter-select"
                disabled={Boolean(window.__CLAIM_LIST_CURRENT_ADVISOR__)}
            >

              <option value="">
                Select Advisor
              </option>

              {window.__CLAIM_LIST_CURRENT_ADVISOR__ ? <option value={window.__CLAIM_LIST_CURRENT_ADVISOR__.name}>{window.__CLAIM_LIST_CURRENT_ADVISOR__.name}</option> : <option value="Anil Shinde">Anil Shinde</option>}

            </select>

          </FilterField>


          {/* Claim Type */}

          <FilterField label="Claim Type">

            <select
              name="claimType"
              value={filters.claimType}
              onChange={handleFilterChange}
              className="claim-filter-select"
            >

              <option value="">
                Claim Type
              </option>

              <option value="Cashless">
                Cashless
              </option>

              <option value="Reimbursement">
                Reimbursement
              </option>

            </select>

          </FilterField>

        </div>


        {/* SEARCH + ACTIONS */}

        <div className="claim-filter-actions">

          <div className="claim-filter-search">

            <div className="claim-search-wrapper">

              <Search size={15} />

              <input
                type="text"
                name="search"
                value={filters.search}
                onChange={handleFilterChange}
                placeholder="Search by Claim No, Customer, Vehicle..."
              />

              {filters.search && (
                <button
                  type="button"
                  onClick={() =>
                    setFilters((previous) => ({
                      ...previous,
                      search: "",
                    }))
                  }
                >
                  <X size={13} />
                </button>
              )}

            </div>

          </div>


          <button
            type="button"
            className="claim-filter-button"
            onClick={handleApplyFilter}
          >

            <Filter size={14} />

            Apply Filter

          </button>


          <button
            type="button"
            className="claim-tool-button"
            onClick={handleReset}
          >

            <RotateCcw size={14} />

            Reset

          </button>


          <div className="claim-filter-spacer" />


          <button
            type="button"
            className="claim-tool-button"
            onClick={handleExport}
          >

            <Download size={14} />

            Export

          </button>


          <button
            type="button"
            className="claim-tool-button"
          >

            <Columns3 size={14} />

            Columns

          </button>

        </div>

      </section>


      {/* ======================================================
          CLAIM TABLE
          ====================================================== */}

      <section className="claim-table-card">

        <div className="claim-table-header">

          <div className="claim-table-title">

            Claims

            <span className="claim-table-count">
              ({filteredClaims.length})
            </span>

          </div>


          <div className="claim-table-tools">

            <span className="claim-showing">

              Showing{" "}

              {filteredClaims.length === 0
                ? 0
                : (currentPage - 1) *
                    pageSize +
                  1}

              {" - "}

              {Math.min(
                currentPage * pageSize,
                filteredClaims.length
              )}

              {" of "}

              {filteredClaims.length}

            </span>

          </div>

        </div>


        <div className="claim-table-wrapper">

          <table className="claim-table">

            <thead>

              <tr>

                <th className="claim-check-column">

                  <input
                    type="checkbox"
                    className="claim-checkbox"
                    checked={
                      paginatedClaims.length > 0 &&
                      selectedClaims.length ===
                        paginatedClaims.length
                    }
                    onChange={handleSelectAll}
                  />

                </th>


                <SortableHeader
                  title="Claim No"
                  field="claimNo"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />


                <SortableHeader
                  title="Reg No"
                  field="regNo"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />


                <th>
                  Customer
                </th>


                <th>
                  Mobile
                </th>


                <th>
                  Model
                </th>


                <th>
                  Advisor
                </th>


                <SortableHeader
                  title="Created Date"
                  field="createdDate"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />


                <th>
                  Ins. Co.
                </th>


                <th>
                  IC Claim No
                </th>


                <th>
                  Accident Date
                </th>


                <th>
                  Intimation Date
                </th>


                <th>
                  Remarks
                </th>


                <SortableHeader
                  title="Days Since Intimation"
                  field="daysSinceIntimation"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />


                <th>
                  Stage
                </th>


                <th>
                  Action
                </th>

              </tr>

            </thead>


            <tbody>

              {paginatedClaims.length === 0 ? (

                <tr>

                  <td
                    colSpan="16"
                    className="claim-empty"
                  >

                    <FileText size={35} />

                    <strong>
                      No claims found
                    </strong>

                    <span>
                      Try changing your filters
                      or search criteria.
                    </span>

                  </td>

                </tr>

              ) : (

                paginatedClaims.map(
                  (claim) => (

                    <tr key={claim.id}>

                      {/* CHECKBOX */}

                      <td>

                        <input
                          type="checkbox"
                          className="claim-checkbox"
                          checked={selectedClaims.includes(
                            claim.id
                          )}
                          onChange={() =>
                            handleSelectClaim(
                              claim.id
                            )
                          }
                        />

                      </td>


                      {/* CLAIM NO */}

                      <td>

                        <button
                          className="claim-number-link"
                          type="button"
                          onClick={() =>
                            handleEditClaim(
                              claim
                            )
                          }
                        >
                          {claim.claimNo}
                        </button>

                      </td>


                      {/* REG NO */}

                      <td>

                        <strong className="claim-reg-no">
                          {claim.regNo}
                        </strong>

                      </td>


                      {/* CUSTOMER */}

                      <td>
                        {claim.customer}
                      </td>


                      {/* MOBILE */}

                      <td>
                        {claim.mobile}
                      </td>


                      {/* MODEL */}

                      <td>
                        {claim.model}
                      </td>


                      {/* ADVISOR */}

                      <td>

                        <span className="claim-advisor">
                          {claim.advisor ||
                            "Unassigned"}
                        </span>

                      </td>


                      {/* CREATED DATE */}

                      <td>

                        <span className="claim-created">
                          {formatDateTime(
                            claim.createdDate
                          )}
                        </span>

                      </td>


                      {/* INSURANCE */}

                      <td>

                        <span
                          className="claim-insurance"
                          title={
                            claim.insuranceCompany
                          }
                        >
                          {claim.insuranceCompany ||
                            "-"}
                        </span>

                      </td>


                      {/* IC CLAIM */}

                      <td>
                        {claim.icClaimNo ||
                          "-"}
                      </td>


                      {/* ACCIDENT DATE */}

                      <td>
                        {formatDate(
                          claim.accidentDate
                        )}
                      </td>


                      {/* INTIMATION DATE */}

                      <td>
                        {formatDate(
                          claim.intimationDate
                        )}
                      </td>


                      {/* REMARKS */}

                      <td>

                        <span className="claim-remarks">
                          {claim.remarks ||
                            "-"}
                        </span>

                      </td>


                      {/* DAYS */}

                      <td>

                        <span
                          className={`claim-days ${getDaysClass(
                            claim.daysSinceIntimation
                          )}`}
                        >
                          {claim.daysSinceIntimation}
                        </span>

                      </td>


                      {/* STAGE */}

                      <td>

                        <span
                          className={`claim-stage-badge ${
                            STAGE_CLASS[
                              claim.stage
                            ] || "advisor"
                          }`}
                        >
                          {claim.stage}
                        </span>

                      </td>


                      {/* ACTION */}

                      <td>

                        <button
                          type="button"
                          className="claim-edit-button"
                          onClick={() =>
                            handleEditjobCard(
                              claim
                            )
                          }
                        >

                          <Pencil size={12} />

                          Edit Claim

                        </button>

                      </td>

                    </tr>

                  )
                )

              )}

            </tbody>

          </table>

        </div>


        {/* ====================================================
            TABLE FOOTER
            ==================================================== */}

        <div className="claim-table-footer">

          <div className="claim-total">

            Total{" "}
            <strong>
              {filteredClaims.length}
            </strong>{" "}
            claims

          </div>


          <div className="claim-pagination">

            <button
              type="button"
              className="claim-page-button"
              disabled={currentPage === 1}
              onClick={() =>
                setCurrentPage(
                  (previous) =>
                    Math.max(
                      1,
                      previous - 1
                    )
                )
              }
            >

              <ChevronLeft size={15} />

            </button>


            {Array.from(
              { length: totalPages },
              (_, index) =>
                index + 1
            )
              .slice(0, 5)
              .map((page) => (

                <button
                  key={page}
                  type="button"
                  className={`claim-page-button ${
                    currentPage === page
                      ? "active"
                      : ""
                  }`}
                  onClick={() =>
                    setCurrentPage(page)
                  }
                >
                  {page}
                </button>

              ))}


            <button
              type="button"
              className="claim-page-button"
              disabled={
                currentPage === totalPages
              }
              onClick={() =>
                setCurrentPage(
                  (previous) =>
                    Math.min(
                      totalPages,
                      previous + 1
                    )
                )
              }
            >

              <ChevronRight size={15} />

            </button>

          </div>

        </div>

      </section>

    </div>
  );
}


/* ============================================================
   SUMMARY CARD COMPONENT
   ============================================================ */

function SummaryCard({
  type,
  icon,
  label,
  value,
}) {

  return (

    <div
      className={`claim-summary-card ${type}`}
    >

      <div className="claim-summary-icon">
        {icon}
      </div>

      <div>

        <span className="claim-summary-label">
          {label}
        </span>

        <strong className="claim-summary-value">
          {value}
        </strong>

      </div>

    </div>

  );
}


/* ============================================================
   FILTER FIELD COMPONENT
   ============================================================ */

function FilterField({
  label,
  children,
}) {

  return (

    <div className="claim-filter-group">

      <label>
        {label}
      </label>

      {children}

    </div>

  );
}


/* ============================================================
   SORTABLE HEADER
   ============================================================ */

function SortableHeader({
  title,
  field,
  currentField,
  direction,
  onSort,
}) {

  const active =
    currentField === field;

  return (

    <th>

      <button
        type="button"
        className="claim-sort-button"
        onClick={() =>
          onSort(field)
        }
      >

        <span>
          {title}
        </span>

        {active ? (

          <ArrowUpDown
            size={11}
            className={
              direction === "asc"
                ? "sort-asc"
                : "sort-desc"
            }
          />

        ) : (

          <ArrowUpDown size={10} />

        )}

      </button>

    </th>

  );
}
