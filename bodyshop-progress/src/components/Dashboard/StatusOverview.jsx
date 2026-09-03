export default function StatusOverview() {
  const statuses = [
    {
      name: "Pending",
      value: 12,
      type: "pending",
    },
    {
      name: "In Progress",
      value: 8,
      type: "progress",
    },
    {
      name: "Completed",
      value: 24,
      type: "completed",
    },
    {
      name: "Delivered",
      value: 18,
      type: "delivered",
    },
  ];

  return (
    <div className="dashboard-panel">
      <div className="dashboard-panel-header">
        <div>
          <h2>Job Status Overview</h2>
          <p>Current workshop activity</p>
        </div>
      </div>

      <div className="status-list">
        {statuses.map((status) => (
          <div className="status-row" key={status.name}>
            <div className="status-info">
              <span className={`status-dot ${status.type}`}></span>

              <span>{status.name}</span>
            </div>

            <strong>{status.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}