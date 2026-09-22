
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import InsuranceMaster from "./components/InsuranceMaster/InsuranceMaster";
import "./components/InsuranceMaster/InsuranceMaster.css";

const root = document.getElementById("insurance-master-react-root");

if (root) {
  createRoot(root).render(
    <StrictMode>
      <InsuranceMaster />
    </StrictMode>
  );
}

