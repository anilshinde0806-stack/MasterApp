import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],

  build: {
    rollupOptions: {
      input: {

  main: resolve(
    __dirname,
    "index.html"
  ),

  vehicle: resolve(
    __dirname,
    "src/vehicle-main.jsx"
  ),

  dashboard: resolve(
    __dirname,
    "src/dashboard-main.jsx"
  ),

  menu: resolve(
    __dirname,
    "src/menu-main.jsx"
  ),

  header: resolve(
    __dirname,
    "src/header-main.jsx"
  ),

  toast: resolve(
    __dirname,
    "src/toast-main.jsx"
  ),

  claim: resolve(
    __dirname,
    "src/claim-main.jsx"
  ),
  assessment: resolve(__dirname, "src/assessment-main.jsx"),
  claimList: resolve(__dirname, "src/claim-list-main.jsx"),
  jobCards: resolve(__dirname, "src/jobcards-main.jsx"),
  insurance: resolve(
    __dirname,
    "src/insurance-main.jsx"
  ),
  jobcard: resolve(
    __dirname,
    "src/jobcard-main.jsx"
  ),
  quality: resolve(
    __dirname,
    "src/quality-main.jsx"
  )

},

      output: {
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name].[ext]",
      },
    },

    manifest: true,
  },
});
