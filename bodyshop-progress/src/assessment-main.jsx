import { useState } from "react";
import { createRoot } from "react-dom/client";

import AssessmentModal from "./components/Assessment/AssessmentModal";
import "./assessment.css";

function App() {
  const [open, setOpen] = useState(false);
  const payload = window.__ASSESSMENT_ENTRY__ || {};

  return (
    <>
      <button
        type="button"
        className="assessment-react-open"
        onClick={() => setOpen(true)}
      >
        Open Assessment
      </button>

      <AssessmentModal
        jobId={payload.jobId}
        open={open}
        onClose={() => setOpen(false)}
        mode={payload.mode || "assessment"}
      />
    </>
  );
}

const root = document.getElementById("assessmentReactRoot");

if (root) {
  createRoot(root).render(<App />);
}
