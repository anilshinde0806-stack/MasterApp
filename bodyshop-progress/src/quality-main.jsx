
import { createRoot } from "react-dom/client";

import QualityCheck from "./components/QC/QualityCheck";

function getJobId() {
  const root = document.getElementById("quality-check-root");

  // Preferred: data-job-id on the Django template root.
  if (root?.dataset?.jobId) {
    return root.dataset.jobId;
  }

  // Optional Django/React bootstrap payload.
  if (window.__QUALITY_CHECK__?.jobId) {
    return window.__QUALITY_CHECK__.jobId;
  }

  // Fallback: /jobCard/<id>/quality-check/
  const match = window.location.pathname.match(
    /\/jobCard\/(\d+)\/quality-check\/?/
  );

  return match ? match[1] : null;
}

function QualityCheckApp() {
  const jobId = getJobId();

  if (!jobId) {
    return (
      <div
        style={{
          padding: 24,
          color: "#b91c1c",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <strong>Quality Check Job Card ID not found.</strong>
      </div>
    );
  }

  return <QualityCheck jobId={jobId} />;
}

const root = document.getElementById("quality-check-root");

if (root) {
  createRoot(root).render(<QualityCheckApp />);
}
