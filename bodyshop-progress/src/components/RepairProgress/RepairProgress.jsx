import React, { useMemo, useState } from "react";
import {
  Wrench,
  CheckCircle2,
  Clock3,
  Pause,
  Circle,
  Eye,
  UserRound,
  CalendarDays,
  Timer,
  CarFront,
  Paintbrush,
  Hammer,
  Settings2,
  PackageCheck,
  ChevronRight,
  AlertCircle,
  CircleDot,
} from "lucide-react";

import "./RepairProgress.css";

function getStatusLabel(status) {
  switch (status) {
    case "completed":
      return "Completed";

    case "in-progress":
      return "In Progress";

    case "paused":
      return "Paused";

    case "pending":
    default:
      return "Pending";
  }
}

function StatusBadge({ status }) {
  const Icon =
    status === "completed"
      ? CheckCircle2
      : status === "in-progress"
      ? CircleDot
      : status === "paused"
      ? Pause
      : Circle;

  return (
    <span className={`rp-status-badge ${status}`}>
      <Icon size={14} strokeWidth={2.2} />
      {getStatusLabel(status)}
    </span>
  );
}

function ProgressBar({ value, compact = false }) {
  return (
    <div className={`rp-progress-bar ${compact ? "compact" : ""}`}>
      <div
        className="rp-progress-fill"
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  );
}
const normalizeStatus = (status) => {
  const value = String(status || "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ");

  if (value === "completed") return "completed";
  if (value === "in progress") return "in-progress";
  if (value === "paused") return "paused";

  return "pending";
};

const getStageProgress = (status) => {
  const normalized = normalizeStatus(status);
  return normalized === "completed" ? 100 : 0;
};

const STAGE_ICONS = [
  Wrench,
  Settings2,
  Hammer,
  Paintbrush,
  PackageCheck,
  Settings2,
];

const getPhotoUrl = (photo) => {
  if (!photo) return "";

  if (typeof photo === "string") return photo;

  return (
    photo.url ||
    photo.image_url ||
    photo.photo_url ||
    photo.src ||
    photo.file_url ||
    photo.file ||
    photo.image ||
    ""
  );
};

const getPhotoName = (photo, index) => {
  if (!photo || typeof photo === "string") return `Photo ${index + 1}`;

  return (
    photo.caption ||
    photo.name ||
    photo.filename ||
    photo.file_name ||
    `Photo ${index + 1}`
  );
};

const formatTimestamp = (timestamp, fallback = "—") => {
  if (!timestamp) return fallback;

  const date = new Date(Number(timestamp));
  if (Number.isNaN(date.getTime())) return fallback;

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
};

function RepairProgress({ jobProgress = [], jobRepairStatus = "" }) {
    console.log(
  "JOB PROGRESS PHOTOS:",
  jobProgress.map((stage) => ({
    label: stage.label,
    photos: stage.photos,
    photoCount: Array.isArray(stage.photos) ? stage.photos.length : "NOT ARRAY",
  }))
);
  const stages = useMemo(
    () =>
      jobProgress.map((item, index) => {
        const status = normalizeStatus(item.status);

        return {
          id: index + 1,
          name: item.label || `Stage ${index + 1}`,
          shortName: item.label || `Stage ${index + 1}`,
          status,
          progress: getStageProgress(item.status),
          technician: item.employee || null,
          startTime: item.start_timestamp
            ? formatTimestamp(item.start_timestamp)
            : item.start_time || null,
          finishTime: item.finish_timestamp
            ? formatTimestamp(item.finish_timestamp)
            : item.finish_time || null,
          remarks: item.remarks || "",
          photos: item.photos || [],
          icon: STAGE_ICONS[index] || Settings2,
          raw: item,
        };
      }),
    [jobProgress]
  );

  const activities = useMemo(
    () =>
      stages.map((stage) => ({
        id: stage.id,
        activity: stage.name,
        technician: stage.technician || "—",
        start: stage.startTime || "—",
        end: stage.finishTime || "—",
        status: stage.status,
        progress: stage.progress,
      })),
    [stages]
  );

  const [selectedStageId, setSelectedStageId] = useState(() => {
    const activeIndex = jobProgress.findIndex(
      (item) => normalizeStatus(item.status) === "in-progress"
    );

    if (activeIndex >= 0) return activeIndex + 1;

    const pendingIndex = jobProgress.findIndex(
      (item) => normalizeStatus(item.status) !== "completed"
    );

    return pendingIndex >= 0 ? pendingIndex + 1 : 1;
  });

  const [showDetails, setShowDetails] = useState(false);

  const isJobCompleted =
    String(jobRepairStatus || "").trim().toLowerCase() === "completed";

  const visibleStages = useMemo(() => {
    if (isJobCompleted) {
      return stages.filter((stage) => stage.status === "completed");
    }

    return stages;
  }, [stages, isJobCompleted]);

  const currentStage = useMemo(() => {
    return (
      stages.find((stage) => stage.id === selectedStageId) ||
      stages.find((stage) => stage.status === "in-progress") ||
      stages.find((stage) => stage.status === "pending") ||
      stages[0]
    );
  }, [stages, selectedStageId]);

  const overallProgress = useMemo(() => {
    if (!stages.length) return 0;

    return Math.round(
      (stages.filter((stage) => stage.status === "completed").length /
        stages.length) *
        100
    );
  }, [stages]);

  const completedStages = stages.filter(
    (stage) => stage.status === "completed"
  ).length;

  const inProgressStages = stages.filter(
    (stage) => stage.status === "in-progress"
  ).length;

  const pendingStages = stages.filter(
    (stage) => stage.status === "pending"
  ).length;

  const handleStageClick = (stage) => {
    setSelectedStageId(stage.id);
    setShowDetails(false);
  };

  return (
    <div className="repair-progress-page">

      {/* =========================================================
          HEADER
      ========================================================== */}

      <div className="rp-page-header">
        <div className="rp-header-left">
          <div className="rp-header-icon">
            <Wrench size={21} />
          </div>

          <div>
            <h2>Repair Progress</h2>
            <p>Track workshop repair activities and technician progress</p>
          </div>
        </div>

        <div className="rp-header-right">
          <div className="rp-job-mini-card">
            <CarFront size={17} />

            <div>
              <span>Job Card</span>
              <strong>JC-2026-00125</strong>
            </div>
          </div>

          <div className="rp-registration">
            MH 12 AB 1234
          </div>
        </div>
      </div>

      {/* =========================================================
          SUMMARY CARDS
      ========================================================== */}

      <div className="rp-summary-grid">

        <div className="rp-summary-card overall">
          <div className="rp-summary-card-top">
            <span>Overall Progress</span>

            <div className="rp-summary-icon">
              <Wrench size={18} />
            </div>
          </div>

          <div className="rp-overall-number">
            {overallProgress}
            <span>%</span>
          </div>

          <ProgressBar value={overallProgress} />

          <div className="rp-summary-footer">
            <span>Repair completion</span>
            <strong>{completedStages}/{stages.length} stages</strong>
          </div>
        </div>

        <div className="rp-summary-card">
          <div className="rp-summary-card-top">
            <span>Completed</span>

            <div className="rp-summary-icon success">
              <CheckCircle2 size={18} />
            </div>
          </div>

          <div className="rp-summary-number">
            {completedStages}
          </div>

          <div className="rp-summary-label">
            Stages completed
          </div>
        </div>

        <div className="rp-summary-card">
          <div className="rp-summary-card-top">
            <span>In Progress</span>

            <div className="rp-summary-icon active">
              <Clock3 size={18} />
            </div>
          </div>

          <div className="rp-summary-number">
            {inProgressStages}
          </div>

          <div className="rp-summary-label">
            Active stage
          </div>
        </div>

        <div className="rp-summary-card">
          <div className="rp-summary-card-top">
            <span>Pending</span>

            <div className="rp-summary-icon pending">
              <Circle size={18} />
            </div>
          </div>

          <div className="rp-summary-number">
            {pendingStages}
          </div>

          <div className="rp-summary-label">
            Stages remaining
          </div>
        </div>

      </div>

      {/* =========================================================
          STAGE PROGRESS
      ========================================================== */}

      <section className="rp-section">

        <div className="rp-section-header">
          <div>
            <h3>Repair Stages</h3>
            <p>Current workshop execution status</p>
          </div>

          <div className="rp-stage-counter">
            {completedStages} of {stages.length} completed
          </div>
        </div>

        <div className="rp-stage-wrapper">

          {visibleStages.map((stage, index) => {
            const StageIcon = stage.icon;
            const isCompleted = stage.status === "completed";
            const isActive = stage.status === "in-progress";

            return (
              <React.Fragment key={stage.id}>
                <button
                  type="button"
                  className={`rp-stage-item ${
                    selectedStageId === stage.id ? "selected" : ""
                  } ${stage.status}`}
                  onClick={() => handleStageClick(stage)}
                >
                  <div className="rp-stage-circle">
                    {isCompleted ? (
                      <CheckCircle2 size={21} />
                    ) : (
                      <StageIcon size={20} />
                    )}
                  </div>

                  <div className="rp-stage-content">
                    <span className="rp-stage-name">
                      {stage.name}
                    </span>

                    <span className="rp-stage-progress-text">
                      {isCompleted ? "Completed" : isActive ? "In Progress" : "Pending"}
                    </span>
                  </div>

                  {index < visibleStages.length - 1 && (
                    <ChevronRight
                      className="rp-stage-arrow"
                      size={17}
                    />
                  )}
                </button>
              </React.Fragment>
            );
          })}

        </div>
      </section>

      {/* =========================================================
          CURRENT WORK — READ ONLY
      ========================================================== */}

      {currentStage && (
        <section className="rp-current-section">
          <div className="rp-current-card">
            <div className="rp-current-header">
              <div className="rp-current-title">
                <div className="rp-current-icon">
                  {React.createElement(currentStage.icon || Wrench, { size: 23 })}
                </div>

                <div>
                  <div className="rp-current-title-line">
                    <h3>{currentStage.name}</h3>
                    <StatusBadge status={currentStage.status} />
                  </div>
                  <p>Workshop repair progress</p>
                </div>
              </div>

              <div className="rp-current-percentage">
                <strong>{currentStage.progress}%</strong>
                <span>Complete</span>
              </div>
            </div>

            <div className="rp-current-progress">
              <ProgressBar value={currentStage.progress} />
              <div className="rp-progress-scale">
                <span>0%</span>
                <span>25%</span>
                <span>50%</span>
                <span>75%</span>
                <span>100%</span>
              </div>
            </div>

            <div className="rp-current-details">
              <div className="rp-detail-item">
                <div className="rp-detail-icon"><UserRound size={17} /></div>
                <div>
                  <span>Technician</span>
                  <strong>{currentStage.technician || "Not Assigned"}</strong>
                </div>
              </div>

              <div className="rp-detail-item">
                <div className="rp-detail-icon"><CalendarDays size={17} /></div>
                <div>
                  <span>Started</span>
                  <strong>{currentStage.startTime || "Not Started"}</strong>
                </div>
              </div>

              <div className="rp-detail-item">
                <div className="rp-detail-icon"><Timer size={17} /></div>
                <div>
                  <span>Finished</span>
                  <strong>{currentStage.finishTime || "Not Finished"}</strong>
                </div>
              </div>
            </div>

            <div className="rp-current-actions">
              <button
                type="button"
                className="rp-btn secondary"
                onClick={() => setShowDetails(!showDetails)}
              >
                <Eye size={17} />
                {showDetails ? "Hide Details" : "View Details"}
              </button>
            </div>

            {showDetails && (
              <div className="rp-details-panel">
                <div className="rp-details-panel-header">
                  <h4>Activity Details</h4>
                  <span>{currentStage.name}</span>
                </div>

                <div className="rp-details-grid">
                  <div>
                    <label>Status</label>
                    <strong>{getStatusLabel(currentStage.status)}</strong>
                  </div>
                  <div>
                    <label>Technician</label>
                    <strong>{currentStage.technician || "Not Assigned"}</strong>
                  </div>
                  <div>
                    <label>Start Time</label>
                    <strong>{currentStage.startTime || "Not Started"}</strong>
                  </div>
                  <div>
                    <label>Finish Time</label>
                    <strong>{currentStage.finishTime || "Not Finished"}</strong>
                  </div>
                </div>

                <div className="rp-remarks">
                  <label>Technician Remarks</label>
                  <p>{currentStage.remarks || "No remarks recorded."}</p>
                </div>

                <div className="rp-photo-section">
                  <label>Stage Photos</label>

                  {currentStage.photos?.length > 0 ? (
                    <div className="rp-photo-grid">
                      {currentStage.photos.map((photo, index) => {
                        const photoUrl = getPhotoUrl(photo);

                        if (!photoUrl) return null;

                        return (
                          <a
                            key={photo.id || `${currentStage.id}-photo-${index}`}
                            href={photoUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="rp-photo-card"
                            title="Open photo"
                          >
                            <img
                              src={photoUrl}
                              alt={`${currentStage.name} - ${getPhotoName(photo, index)}`}
                              className="rp-photo-image"
                              loading="lazy"
                            />

                            <div className="rp-photo-meta">
                              <strong>{getPhotoName(photo, index)}</strong>
                              <span>View</span>
                            </div>
                          </a>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="rp-photo-empty">
                      No photos uploaded for this stage.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* =========================================================
          REPAIR ACTIVITIES
      ========================================================== */}

      <section className="rp-section">

        <div className="rp-section-header">
          <div>
            <h3>Repair Activities</h3>
            <p>Workshop activity timeline</p>
          </div>

          <div className="rp-stage-counter">
            Read only
          </div>
        </div>

        <div className="rp-table-container">

          <table className="rp-table">

            <thead>
              <tr>
                <th>Activity</th>
                <th>Technician</th>
                <th>Start</th>
                <th>Finish</th>
                <th>Status</th>
                <th>Progress</th>
              </tr>
            </thead>

            <tbody>

              {activities.map((activity) => (
                <tr key={activity.id}>

                  <td>
                    <div className="rp-activity-name">
                      <span className="rp-activity-dot" />
                      <strong>{activity.activity}</strong>
                    </div>
                  </td>

                  <td>
                    <div className="rp-technician-cell">
                      <div className="rp-avatar">
                        {activity.technician !== "—"
                          ? activity.technician
                              .split(" ")
                              .map((word) => word[0])
                              .join("")
                              .slice(0, 2)
                          : "—"}
                      </div>

                      <span>
                        {activity.technician}
                      </span>
                    </div>
                  </td>

                  <td>{activity.start}</td>

                  <td>{activity.end}</td>

                  <td>
                    <StatusBadge
                      status={activity.status}
                    />
                  </td>

                  <td>
                    <div className="rp-table-progress">

                      <ProgressBar
                        value={activity.progress}
                        compact
                      />

                      <span>
                        {activity.progress}%
                      </span>

                    </div>
                  </td>


                </tr>
              ))}

            </tbody>

          </table>

        </div>

      </section>

      {/* =========================================================
          BOTTOM INFORMATION
      ========================================================== */}

      <div className="rp-information-banner">

        <div className="rp-information-icon">
          <AlertCircle size={19} />
        </div>

        <div>
          <strong>Repair workflow information</strong>

          <p>
            Repair progress is displayed from the workshop WorkProgress
            records. This tab is read-only for the Advisor.
          </p>
        </div>

      </div>

    </div>
  );
}

export default RepairProgress;