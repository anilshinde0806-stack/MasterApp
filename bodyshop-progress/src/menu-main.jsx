import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";
import Menu from "./components/Menu/Menu";

const rootElement = document.getElementById("react-menu-root");

if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <Menu />
    </StrictMode>
  );
}