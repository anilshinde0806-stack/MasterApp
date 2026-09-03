import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import ERPHeader from "./components/Header/ERPHeader";


const rootElement =
  document.getElementById("erp-header-root");


if (rootElement) {

  createRoot(rootElement).render(

    <StrictMode>

      <ERPHeader />

    </StrictMode>

  );

}