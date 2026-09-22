
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import ClaimList from "./components/Claim/ClaimList";

const root = document.getElementById("claimListReactRoot");

if (root) {
  createRoot(root).render(
    <StrictMode>
      <ClaimList />
    </StrictMode>
  );
}
