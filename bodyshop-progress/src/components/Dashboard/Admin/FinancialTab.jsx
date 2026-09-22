import React from "react";
import "./FinancialTab.css";

import {
  IndianRupee,
  TrendingUp,
  Package,
  Wrench,
  FileText,
  Wallet,
  CircleDollarSign,
  Receipt,
  BarChart3,
} from "lucide-react";


export default function FinancialTab({ data }) {

  const financial = data?.financial || {};

  const revenue = data?.revenue || {};


  // ==========================================
  // FORMAT CURRENCY
  // ==========================================

  const formatCurrency = (value) => {

    const amount = Number(value || 0);

    if (amount >= 100000) {
      return `₹ ${(amount / 100000).toFixed(2)} L`;
    }

    if (amount >= 1000) {
      return `₹ ${(amount / 1000).toFixed(1)} K`;
    }

    return `₹ ${amount.toFixed(0)}`;
  };


  // ==========================================
  // FINANCIAL KPI CARDS
  // ==========================================

  const financialCards = [

    {
      title: "Estimated Revenue",
      value: financial.estimate ?? revenue.total ?? 0,
      icon: TrendingUp,
      color: "#2563EB",
    },

    {
      title: "Total Revenue",
      value: revenue.total ?? 0,
      icon: IndianRupee,
      color: "#16A34A",
    },

    {
      title: "Parts Revenue",
      value: revenue.parts ?? 0,
      icon: Package,
      color: "#0891B2",
    },

    {
      title: "Labour Revenue",
      value: revenue.labour ?? 0,
      icon: Wrench,
      color: "#F97316",
    },

    {
      title: "Invoice",
      value: financial.invoice ?? 0,
      icon: Receipt,
      color: "#7C3AED",
    },

    {
      title: "Collection",
      value: financial.collection ?? 0,
      icon: Wallet,
      color: "#059669",
    },

    {
      title: "Outstanding",
      value: financial.outstanding ?? 0,
      icon: CircleDollarSign,
      color: "#DC2626",
    },

    {
      title: "Average Job Value",
      value: financial.average_job_value ?? 0,
      icon: BarChart3,
      color: "#DB2777",
    },

  ];


  return (

    <div className="financial-dashboard">


      {/* ======================================
          FINANCIAL HEADER
      ====================================== */}

      <div className="financial-title-section">

        <div>

          <h2>Financial Dashboard</h2>

          <p>
            Revenue, billing and collection overview
          </p>

        </div>


        <div className="financial-title-icon">

          <IndianRupee size={22} />

        </div>

      </div>



      {/* ======================================
          FINANCIAL SUMMARY
      ====================================== */}

      <section className="financial-summary-grid">

        {financialCards.map((card) => {

          const Icon = card.icon;

          return (

            <div
              className="financial-card"
              key={card.title}
              style={{
                "--card-color": card.color
              }}
            >

              <div className="financial-card-icon">

                <Icon size={21} />

              </div>


              <div className="financial-card-content">

                <span className="financial-card-title">

                  {card.title}

                </span>


                <strong className="financial-card-value">

                  {formatCurrency(card.value)}

                </strong>

              </div>

            </div>

          );

        })}

      </section>



      {/* ======================================
          REVENUE BREAKDOWN
      ====================================== */}

      <section className="financial-bottom-grid">


        {/* REVENUE BREAKDOWN */}

        <div className="financial-panel">

          <div className="financial-panel-header">

            <div>

              <h3>Revenue Breakdown</h3>

              <p>
                Revenue distribution by category
              </p>

            </div>

          </div>


          <div className="revenue-breakdown">


            <RevenueRow
              label="Total Revenue"
              value={revenue.total}
              color="#2563EB"
              total={revenue.total}
            />


            <RevenueRow
              label="Parts Revenue"
              value={revenue.parts}
              color="#0891B2"
              total={revenue.total}
            />


            <RevenueRow
              label="Labour Revenue"
              value={revenue.labour}
              color="#F97316"
              total={revenue.total}
            />


          </div>

        </div>



        {/* FINANCIAL HEALTH */}

        <div className="financial-panel">

          <div className="financial-panel-header">

            <div>

              <h3>Financial Health</h3>

              <p>
                Current billing and payment position
              </p>

            </div>

          </div>


          <div className="financial-health-grid">


            <HealthItem
              label="Invoice"
              value={financial.invoice}
              color="#7C3AED"
            />


            <HealthItem
              label="Collection"
              value={financial.collection}
              color="#059669"
            />


            <HealthItem
              label="Outstanding"
              value={financial.outstanding}
              color="#DC2626"
            />


          </div>

        </div>


      </section>


    </div>

  );

}



/* ==========================================
   REVENUE ROW
========================================== */

function RevenueRow({
  label,
  value,
  total,
  color
}) {

  const amount = Number(value || 0);

  const totalAmount = Number(total || 0);

  const percentage =
    totalAmount > 0
      ? Math.min(
          (amount / totalAmount) * 100,
          100
        )
      : 0;


  const formatCurrency = (value) => {

    const amount = Number(value || 0);

    if (amount >= 100000) {
      return `₹ ${(amount / 100000).toFixed(2)} L`;
    }

    if (amount >= 1000) {
      return `₹ ${(amount / 1000).toFixed(1)} K`;
    }

    return `₹ ${amount.toFixed(0)}`;
  };


  return (

    <div className="revenue-row">

      <div className="revenue-row-top">

        <span>{label}</span>

        <strong>
          {formatCurrency(amount)}
        </strong>

      </div>


      <div className="revenue-progress">

        <div
          className="revenue-progress-fill"
          style={{
            width: `${percentage}%`,
            background: color
          }}
        />

      </div>

    </div>

  );

}



/* ==========================================
   FINANCIAL HEALTH ITEM
========================================== */

function HealthItem({
  label,
  value,
  color
}) {

  const amount = Number(value || 0);


  const formatCurrency = (value) => {

    if (value >= 100000) {
      return `₹ ${(value / 100000).toFixed(2)} L`;
    }

    if (value >= 1000) {
      return `₹ ${(value / 1000).toFixed(1)} K`;
    }

    return `₹ ${value.toFixed(0)}`;
  };


  return (

    <div
      className="financial-health-item"
      style={{
        "--health-color": color
      }}
    >

      <span>{label}</span>

      <strong>
        {formatCurrency(amount)}
      </strong>

    </div>

  );

}