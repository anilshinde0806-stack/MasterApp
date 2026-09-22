import VehicleMaster from "./components/VehicleMaster/VehicleMaster";
import NewVehicle from "./components/VehicleMaster/NewVehicle";
import VehicleMasterView from "./components/VehicleMaster/VehicleMasterView";
import DriverMaster from "./components/VehicleMaster/DriverMaster";

function VehicleMasterApp() {
  const path = window.location.pathname;

  // Driver Master
  if (path === "/driver-master/" || path.endsWith("/driver-master/")) {
    return <DriverMaster />;
  }

  // New Vehicle
  if (path.endsWith("/vehicle/new/")) {
    return <NewVehicle />;
  }

  // Edit Vehicle
  if (/\/vehicle\/\d+\/edit\/$/.test(path)) {
    return <NewVehicle />;
  }

  // View Vehicle
  if (/\/vehicle\/\d+\/$/.test(path)) {
    return <VehicleMasterView />;
  }

  // Vehicle Master List
  return <VehicleMaster />;
}

export default VehicleMasterApp;