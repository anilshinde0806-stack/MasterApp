import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ClaimEntry from "./components/Claim/ClaimEntry";
import "./components/Claim/ClaimEntry.css";

const root = document.getElementById("claim-react-root");
if (root) createRoot(root).render(<StrictMode><ClaimEntry /></StrictMode>);
