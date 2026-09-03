import React from "react";

import {
  createRoot,
} from "react-dom/client";

import {
  ToastProvider,
} from "./components/Toast/ToastProvider";


const rootElement =
  document.getElementById(
    "react-toast-root"
  );


if (rootElement) {

  createRoot(rootElement).render(

    <ToastProvider>

      <></>

    </ToastProvider>

  );

}