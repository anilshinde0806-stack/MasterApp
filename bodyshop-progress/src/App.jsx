import ProgressStrip from "./components/ProgressStrip";
import VehicleMaster from "./components/VehicleMaster/VehicleMaster";
import "./App.css";

function App() {
  const payload = window.__BODYSHOP_PROGRESS__ || {};
  return (
    <div className="app">
      <ProgressStrip
        steps={payload.steps}
        currentStep={payload.currentStep}
        jobNumber={payload.jobNumber}
        status={payload.status}
      />
    </div>
  );
}

export default App;
