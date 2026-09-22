
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import Dashboard from "./components/Dashboard/Dashboard";

const root = document.getElementById("dashboard-root");

if (root) {
  createRoot(root).render(
    <StrictMode>
      <Dashboard />
    </StrictMode>
  );
}
