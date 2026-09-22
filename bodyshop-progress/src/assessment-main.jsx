import { createRoot } from "react-dom/client";
import AssessmentModal from "./components/Assessment/AssessmentModal";
import "./assessment.css";

function App() { const [open, setOpen] = React.useState(false); const payload = window.__ASSESSMENT_ENTRY__ || {}; return <><button type="button" className="assessment-react-open" onClick={() => setOpen(true)}>▣ Open Assessment</button><AssessmentModal jobId={payload.jobId} open={open} onClose={() => setOpen(false)} mode={payload.mode || "assessment"} /></>; }
import React from "react";
createRoot(document.getElementById("assessmentReactRoot")).render(<App />);
