import React from "react";
import { createRoot } from "react-dom/client";
import JobCardEntry from "./components/JobCards/JobCardEntry";

const root = document.getElementById("jobcard-react-root");

if (root) {
  createRoot(root).render(<JobCardEntry />);
}