export default function StatCard({ title, value, icon, type }) {
  return (
    <div className={`dashboard-stat-card ${type}`}>
      <div className="dashboard-card-icon">
        <i className={`fa ${icon}`}></i>
      </div>

      <div className="dashboard-card-content">
        <div className="dashboard-card-title">{title}</div>

        <div className="dashboard-card-value">
          {value}
        </div>
      </div>
    </div>
  );
}