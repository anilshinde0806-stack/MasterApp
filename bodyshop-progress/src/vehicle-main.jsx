import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";

import VehicleMasterApp from "./VehicleMasterApp.jsx";

const rootElement = document.getElementById(
  "vehicle-master-root"
);

if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <VehicleMasterApp />
    </StrictMode>
  );
}