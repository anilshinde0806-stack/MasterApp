export default function RecentActivity() {
  const activities = [
    {
      title: "New vehicle added",
      description: "Vehicle registration completed",
      time: "10 minutes ago",
      icon: "fa-car",
    },
    {
      title: "Job status updated",
      description: "Repair moved to In Progress",
      time: "30 minutes ago",
      icon: "fa-wrench",
    },
    {
      title: "Customer added",
      description: "New customer registered",
      time: "1 hour ago",
      icon: "fa-user-plus",
    },
    {
      title: "Job completed",
      description: "Vehicle repair completed",
      time: "2 hours ago",
      icon: "fa-check",
    },
  ];

  return (
    <div className="dashboard-panel">
      <div className="dashboard-panel-header">
        <div>
          <h2>Recent Activity</h2>
          <p>Latest updates from the system</p>
        </div>
      </div>

      <div className="activity-list">
        {activities.map((activity, index) => (
          <div className="activity-item" key={index}>
            <div className="activity-icon">
              <i className={`fa ${activity.icon}`}></i>
            </div>

            <div className="activity-content">
              <strong>{activity.title}</strong>

              <span>{activity.description}</span>
            </div>

            <div className="activity-time">
              {activity.time}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}