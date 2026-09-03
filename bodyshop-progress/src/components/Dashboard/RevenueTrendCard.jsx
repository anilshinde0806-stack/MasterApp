import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";


export default function RevenueTrendCard({
  revenueTrend = [],
}) {

  console.log(
    "RevenueTrendCard received:",
    revenueTrend
  );


  return (

    <div className="revenue-trend-card">


      {/* HEADER */}

      <div className="revenue-trend-header">

        <div className="revenue-trend-title">

          <h3>
            Revenue Trend
          </h3>

           <span>Monthly revenue performance</span>

        </div>


        <div className="revenue-chart-legend">

          <span className="legend-dot"></span>

          Revenue

        </div>

      </div>


      {/* CHART */}

       <div className="revenue-chart-container">

        <ResponsiveContainer
          width="100%"
          height={300}
        >

          <AreaChart
            data={revenueTrend}

            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 10,
            }}
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
                  stopOpacity={0.35}
                />

                <stop
                  offset="95%"
                  stopColor="#2563eb"
                  stopOpacity={0.02}
                />

              </linearGradient>

            </defs>


            <CartesianGrid
              vertical={false}
              strokeDasharray="3 3"
              stroke="#e5e7eb"
            />


            {/* MONTH */}

            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}

              tick={{
                fontSize: 12,
                fill: "#64748b",
              }}
            />


            {/* REVENUE VALUES */}

            <YAxis
              tickLine={false}
              axisLine={false}

              tick={{
                fontSize: 11,
                fill: "#64748b",
              }}

              tickFormatter={(value) => {

                if (value >= 100000) {

                  return `₹${(value / 100000).toFixed(1)}L`;

                }

                if (value >= 1000) {

                  return `₹${(value / 1000).toFixed(0)}K`;

                }

                return `₹${value}`;

              }}
            />


            {/* HOVER TOOLTIP */}

            <Tooltip

              formatter={(value) => [

                `₹${Number(value).toLocaleString("en-IN")}`,

                "Revenue"

              ]}

              labelStyle={{
                color: "#1e293b",
                fontWeight: 600,
              }}

              contentStyle={{
                borderRadius: "10px",
                border: "1px solid #e2e8f0",
                boxShadow:
                  "0 8px 20px rgba(0,0,0,0.08)",
              }}

            />


            {/* REVENUE LINE */}

            <Area
              type="monotone"

              dataKey="revenue"

              name="Revenue"

              stroke="#2563eb"

              strokeWidth={3}

              fill="url(#revenueGradient)"

              dot={{
                r: 5,
                fill: "#2563eb",
                stroke: "#ffffff",
                strokeWidth: 2,
              }}

              activeDot={{
                r: 7,
              }}

            />


          </AreaChart>

        </ResponsiveContainer>

      </div>


    </div>

  );

}