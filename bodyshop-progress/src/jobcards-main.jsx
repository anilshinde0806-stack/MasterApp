import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import JobCards from "./components/JobCards/JobCards";
import "./components/JobCards/JobCards.css";

const jobCardsRoot =
  document.getElementById("job-cards-react-root");

if (jobCardsRoot) {
  createRoot(jobCardsRoot).render(
    <StrictMode>
      <JobCards />
    </StrictMode>
  );
}
