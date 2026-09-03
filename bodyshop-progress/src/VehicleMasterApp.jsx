import VehicleMaster from "./components/VehicleMaster/VehicleMaster";
import NewVehicle from "./components/VehicleMaster/NewVehicle";
import DriverMaster from "./components/VehicleMaster/DriverMaster";

function VehicleMasterApp() {
    const path = window.location.pathname;

    if (path === "/driver-master/" || path.endsWith("/driver-master/")) {
        return <DriverMaster />;
    }

    if (
        path.endsWith("/vehicle/new/") ||
        /\/vehicle\/\d+\/edit\/$/.test(path)
    ) {
        return <NewVehicle />;
    }

    return <VehicleMaster />;
}

export default VehicleMasterApp;