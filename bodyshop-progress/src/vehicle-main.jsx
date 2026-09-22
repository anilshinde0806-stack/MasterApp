import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import VehicleMasterApp from "./VehicleMasterApp.jsx";

console.log("🔥 VEHICLE MASTER JS LOADED");

const rootElement = document.getElementById("vehicle-master-root");

console.log("🔥 ROOT ELEMENT:", rootElement);

if (rootElement) {
  console.log("🔥 MOUNTING REACT");

  createRoot(rootElement).render(
    <StrictMode>
      <VehicleMasterApp />
    </StrictMode>
  );
}