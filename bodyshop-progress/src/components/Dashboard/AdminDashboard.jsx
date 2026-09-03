import React from "react";

import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
} from "recharts";

import "./AdminDashboard.css";


/* =========================================================
   ICON COMPONENT
========================================================= */

const Icon = ({ name }) => (
     <span
      className={`material-symbols-outlined dashboard-icon`}
      style={{
        fontSize: 15,
        lineHeight: 1,
      }}
    >
        {name}
    </span>
);


/* =========================================================
   FORMAT CURRENCY
========================================================= */

const formatCurrency = (value) => {

    const number = Number(value || 0);

    if (number >= 10000000) {
        return `₹ ${(number / 10000000).toFixed(2)} Cr`;
    }

    if (number >= 100000) {
        return `₹ ${(number / 100000).toFixed(2)} L`;
    }

    if (number >= 1000) {
        return `₹ ${(number / 1000).toFixed(1)} K`;
    }

    return `₹ ${number.toLocaleString("en-IN")}`;
};


/* =========================================================
   FORMAT NUMBER
========================================================= */

const formatNumber = (value) => {

    return Number(value || 0).toLocaleString("en-IN");

};


/* =========================================================
   PERIOD OPTIONS
========================================================= */

const PERIOD_OPTIONS = [

    {
        value: "today",
        label: "Today",
    },

    {
        value: "yesterday",
        label: "Yesterday",
    },

    {
        value: "this_week",
        label: "This Week",
    },

    {
        value: "this_month",
        label: "This Month",
    },

    {
        value: "last_month",
        label: "Last Month",
    },

    {
        value: "this_year",
        label: "This Year",
    },

    {
        value: "custom",
        label: "Custom Date Range",
    },

];


/* =========================================================
   SUMMARY CARD
========================================================= */

function SummaryCard({ item }) {

    return (

        <div
            className="summary-card"
            style={{
                "--card-color": item.color || "#2563eb"
            }}
        >

            <div className="summary-icon">

                <span className="material-icons">
      {item.icon}
    </span>

            </div>


            <div className="summary-content">

                <div className="summary-title">
                    {item.title}
                </div>

                <div className="summary-value">
                    {formatNumber(item.value)}
                </div>

                {item.subtitle && (

                    <div className="summary-subtitle">
                        {item.subtitle}
                    </div>

                )}

            </div>

        </div>

    );

}


/* =========================================================
   PERFORMANCE CARD
========================================================= */

function PerformanceCard({
    title,
    value,
    icon,
    color,
}) {

    return (

        <div
            className="performance-card"
            style={{
                "--performance-color": color
            }}
        >

            <div className="performance-top">

                <span className="performance-label">
                    {title}
                </span>


                <div
                    className="performance-icon"
                    style={{
                        color: color
                    }}
                >
                   <span className="material-icons">
                     {icon}
                    </span>
                    

                </div>

            </div>


            <div className="performance-value">
                {value}
            </div>

        </div>

    );

}


/* =========================================================
   REVENUE MINI CARD
========================================================= */

function RevenueCard({
    title,
    value,
    subtitle,
    icon,
    color,
}) {

    return (

        <div className="revenue-mini-card">

            <div
                className="revenue-mini-icon"
                style={{
                    color: color,
                    background: `${color}15`,
                }}
            >
                
                <span className="material-icons">
                    {icon}
                </span>

            </div>


            <div className="revenue-mini-content">

                <div className="revenue-mini-label">
                    {title}
                </div>


                <div className="revenue-mini-value">

                    {formatCurrency(value)}

                </div>


                <div className="revenue-mini-subtitle">

                    {subtitle}

                </div>

            </div>

        </div>

    );

}


/* =========================================================
   FINANCIAL CARD
========================================================= */

function FinancialCard({
    title,
    value,
    icon,
    color,
}) {

    return (

        <div className="financial-card">

            <div className="financial-card-top">

                <span className="financial-label">
                    {title}
                </span>


                <div
                    className="financial-icon"
                    style={{
                        color: color
                    }}
                >

                    <span className="material-icons">
                        {icon}
                    </span >

                </div>

            </div>


            <div className="financial-value">

                {formatCurrency(value)}

            </div>

        </div>

    );

}


/* =========================================================
   CUSTOM TOOLTIP
========================================================= */

function RevenueTooltip({
    active,
    payload,
    label,
}) {

    if (!active || !payload || !payload.length) {
        return null;
    }

    const value = payload[0]?.value || 0;

    return (

        <div className="revenue-tooltip">

            <div className="tooltip-date">
                {label}
            </div>


            <div className="tooltip-value">

                Revenue: {formatCurrency(value)}

            </div>

        </div>

    );

}


/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function AdminDashboard({

    data = {},

    filters = {},

    onApplyFilters,

    branches = [],

}) {


    /* =====================================================
       DATA
    ===================================================== */

    const summaries =
        data.summaries || [];


    const performance =
        data.performance || {};


    const revenue =
        data.revenue || {};


    const financial =
        data.financial || {};


    const trend =
        revenue.trend || [];


    /* =====================================================
       FILTERS
    ===================================================== */

    const {

        branch = "",

        period = "today",

        fromDate = "",

        toDate = "",

        setBranch = () => {},

        setPeriod = () => {},

        setFromDate = () => {},

        setToDate = () => {},

        loading = false,

        onReset = () => {},

    } = filters;


    const isCustomPeriod =
        period === "custom";


    /* =====================================================
       APPLY FILTER
    ===================================================== */

    const handleApply = () => {

        if (typeof onApplyFilters === "function") {

            onApplyFilters();

        }

    };


    return (

        <div className="admin-dashboard">


            {/* =============================================
                HEADER
            ============================================= */}

            <div className="dashboard-header">

                <div>

                    <h1 className="dashboard-title">

                        Admin Dashboard

                    </h1>


                    <p className="dashboard-subtitle">

                        Complete overview of workshop operations,
                        performance and financial activity.

                    </p>

                </div>


                <div className="dashboard-date-badge">

                    <Icon name="dashboard" />

                    <span>
                        Management Overview
                    </span>

                </div>

            </div>



            {/* =============================================
                FILTERS
            ============================================= */}

            <div className="dashboard-filters">


                {/* BRANCH */}

                <div className="filter-group">

                    <label>

                        <Icon name="account_tree" />

                        Branch

                    </label>


                    <select
                        value={branch || ""}
                        onChange={(event) =>
                            setBranch(event.target.value)
                        }
                    >

                        <option value="">
                            All Branches
                        </option>


                        {branches.map((item) => (

                            <option
                                key={
                                    item.id ||
                                    item.pk ||
                                    item.value
                                }

                                value={
                                    item.id ||
                                    item.pk ||
                                    item.value
                                }
                            >

                                {
                                    item.name ||
                                    item.branch_name ||
                                    item.label
                                }

                            </option>

                        ))}

                    </select>

                </div>



                {/* PERIOD */}

                <div className="filter-group">

                    <label>

                        <Icon name="calendar_month" />

                        Period

                    </label>


                    <select
                        value={period || "today"}
                        onChange={(event) =>
                            setPeriod(event.target.value)
                        }
                    >

                        {PERIOD_OPTIONS.map((item) => (

                            <option
                                key={item.value}
                                value={item.value}
                            >

                                {item.label}

                            </option>

                        ))}

                    </select>

                </div>



                {/* CUSTOM DATES */}

                {isCustomPeriod && (

                    <>

                        {/* FROM DATE */}

                        <div className="filter-group">

                            <label>

                                <Icon name="event" />

                                From Date

                            </label>


                            <input
                                type="date"

                                value={fromDate || ""}

                                onChange={(event) =>
                                    setFromDate(
                                        event.target.value
                                    )
                                }
                            />

                        </div>



                        {/* TO DATE */}

                        <div className="filter-group">

                            <label>

                                <Icon name="event_available" />

                                To Date

                            </label>


                            <input
                                type="date"

                                value={toDate || ""}

                                onChange={(event) =>
                                    setToDate(
                                        event.target.value
                                    )
                                }
                            />

                        </div>

                    </>

                )}



                {/* ACTIONS */}

                <div className="filter-actions">


                    <button
                        className="apply-filter-btn"

                        onClick={handleApply}

                        disabled={loading}
                    >

                        <Icon name="filter_alt" />

                        {loading
                            ? "Loading..."
                            : "Apply Filters"
                        }

                    </button>


                    <button
                        className="reset-filter-btn"

                        onClick={onReset}

                        disabled={loading}
                    >

                        <Icon name="restart_alt" />

                        Reset

                    </button>

                </div>


            </div>



            {/* =============================================
                OVERVIEW
            ============================================= */}

            <section className="dashboard-section">


                <div className="section-header">

                    <div>

                        <h2 className="section-title">

                            Overview

                        </h2>


                        <p className="section-subtitle">

                            Current workshop activity

                        </p>

                    </div>

                </div>


                <div className="summary-grid">

                    {summaries.map((item, index) => (

                        <SummaryCard
                            key={
                                item.type ||
                                index
                            }

                            item={item}
                        />

                    ))}

                </div>


            </section>



            {/* =============================================
                WORKSHOP PERFORMANCE
            ============================================= */}

            <section className="dashboard-section">


                <div className="section-header">

                    <div>

                        <h2 className="section-title">

                            Workshop Performance

                        </h2>


                        <p className="section-subtitle">

                            Current job performance overview

                        </p>

                    </div>

                </div>


                <div className="performance-grid">


                    <PerformanceCard
                        title="Total Jobs"

                        value={
                            formatNumber(
                                performance.total_jobs
                            )
                        }

                        icon="assignment"

                        color="#2563eb"
                    />


                    <PerformanceCard
                        title="Completed Jobs"

                        value={
                            formatNumber(
                                performance.completed_jobs
                            )
                        }

                        icon="task_alt"

                        color="#10b981"
                    />


                    <PerformanceCard
                        title="Running Jobs"

                        value={
                            formatNumber(
                                performance.running_jobs
                            )
                        }

                        icon="engineering"

                        color="#f59e0b"
                    />


                    <PerformanceCard
                        title="Pending Jobs"

                        value={
                            formatNumber(
                                performance.pending_jobs
                            )
                        }

                        icon="pending_actions"

                        color="#8b5cf6"
                    />


                    <PerformanceCard
                        title="Completion Rate"

                        value={
                            `${performance.completion_percentage || 0}%`
                        }

                        icon="bar_chart"

                        color="#ec4899"
                    />


                    <PerformanceCard
                        title="Average TAT"

                        value={
                            performance.average_tat || 0
                        }

                        icon="hourglass_top"

                        color="#06b6d4"
                    />


                </div>


            </section>



            {/* =============================================
                REVENUE
            ============================================= */}

            <section className="dashboard-section">


                <div className="section-header">

                    <div>

                        <h2 className="section-title">

                            Revenue Overview

                        </h2>


                        <p className="section-subtitle">

                            Revenue performance for selected period

                        </p>

                    </div>

                </div>


                <div className="revenue-section">


                    {/* REVENUE CARDS */}

                    <div className="revenue-summary-column">


                        <RevenueCard
                            title="Total Revenue"

                            value={revenue.total}

                            subtitle="Overall workshop revenue"

                            icon="currency_rupee"

                            color="#2563eb"
                        />


                        <RevenueCard
                            title="Parts Revenue"

                            value={revenue.parts}

                            subtitle="Revenue generated from parts"

                            icon="settings"

                            color="#10b981"
                        />


                        <RevenueCard
                            title="Labour Revenue"

                            value={revenue.labour}

                            subtitle="Revenue generated from labour"

                            icon="construction"

                            color="#f97316"
                        />


                    </div>



                    {/* REVENUE CHART */}

                    <div className="revenue-chart-card">


                        <div className="chart-header">

                            <div>

                                <h3 className="chart-title">

                                    Revenue Trend

                                </h3>


                                <p className="chart-subtitle">

                                    Revenue performance over time

                                </p>

                            </div>


                            <div className="chart-badge">

                                <Icon name="trending_up" />

                                Revenue

                            </div>

                        </div>


                        <div className="chart-container">


                            {trend.length > 0 ? (

                                <ResponsiveContainer
                                    width="100%"
                                    height="100%"
                                >

                                    <AreaChart
                                        data={trend}
                                    >

                                        <defs>

                                            <linearGradient
                                                id="revenueGradient"

                                                x1="0"

                                                y1="0"

                                                x2="0"

                                                y2="1"
                                            >

                                                <stop
                                                    offset="5%"

                                                    stopColor="#2563eb"

                                                    stopOpacity={0.25}
                                                />


                                                <stop
                                                    offset="95%"

                                                    stopColor="#2563eb"

                                                    stopOpacity={0}
                                                />

                                            </linearGradient>

                                        </defs>


                                        <CartesianGrid
                                            vertical={false}

                                            strokeDasharray="3 3"

                                            stroke="#e2e8f0"
                                        />


                                        <XAxis
                                            dataKey="label"

                                            tick={{
                                                fontSize: 11,
                                                fill: "#64748b"
                                            }}

                                            axisLine={false}

                                            tickLine={false}
                                        />


                                        <YAxis
                                            tick={{
                                                fontSize: 11,
                                                fill: "#64748b"
                                            }}

                                            axisLine={false}

                                            tickLine={false}

                                            tickFormatter={(value) =>
                                                formatCurrency(value)
                                            }
                                        />


                                        <Tooltip
                                            content={
                                                <RevenueTooltip />
                                            }
                                        />


                                        <Area
                                            type="monotone"

                                            dataKey="total"

                                            stroke="#2563eb"

                                            strokeWidth={3}

                                            fill="url(#revenueGradient)"
                                        />

                                    </AreaChart>

                                </ResponsiveContainer>

                            ) : (

                                <div className="chart-empty">

                                    <Icon name="show_chart" />

                                    <span>
                                        No revenue data available
                                        for this period
                                    </span>

                                </div>

                            )}


                        </div>


                    </div>


                </div>


            </section>



            {/* =============================================
                FINANCIAL OVERVIEW
            ============================================= */}

            <section className="dashboard-section">


                <div className="section-header">

                    <div>

                        <h2 className="section-title">

                            Financial Overview

                        </h2>


                        <p className="section-subtitle">

                            Financial performance summary

                        </p>

                    </div>

                </div>


                <div className="financial-grid">


                    <FinancialCard
                        title="Estimate"

                        value={financial.estimate}

                        icon="request_quote"

                        color="#2563eb"
                    />


                    <FinancialCard
                        title="Approved"

                        value={financial.approved}

                        icon="verified"

                        color="#10b981"
                    />


                    <FinancialCard
                        title="Invoice"

                        value={financial.invoice}

                        icon="receipt_long"

                        color="#8b5cf6"
                    />


                    <FinancialCard
                        title="Collection"

                        value={financial.collection}

                        icon="payments"

                        color="#f59e0b"
                    />


                    <FinancialCard
                        title="Outstanding"

                        value={financial.outstanding}

                        icon="account_balance_wallet"

                        color="#ef4444"
                    />


                    <FinancialCard
                        title="Average Job Value"

                        value={financial.average_job_value}

                        icon="analytics"

                        color="#06b6d4"
                    />


                </div>


            </section>


        </div>

    );

}