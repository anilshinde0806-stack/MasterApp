import { useEffect, useMemo, useState } from "react";
import "./VehicleMaster.css";

function VehicleMaster() {


  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  // --------------------------------------------------
  // LOAD VEHICLES
  // --------------------------------------------------

  const loadVehicles = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("/ajax/vehicles/", {
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      setVehicles(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Vehicle API error:", err);
      setError("Unable to load vehicles.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVehicles();
  }, []);

  // --------------------------------------------------
  // SEARCH
  // --------------------------------------------------

  const filteredVehicles = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return vehicles;
    }

    return vehicles.filter((vehicle) => {
      const searchableText = [
        vehicle.registration_no,
        vehicle.chassis_no,
        vehicle.engine_no,
        vehicle.model__name,
        vehicle.variant__name,
        vehicle.color,
        vehicle.customer__name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(query);
    });
  }, [vehicles, search]);

  // --------------------------------------------------
  // NEW VEHICLE
  // --------------------------------------------------

 const handleNewVehicle = () => {
  window.location.href = "/vehicle/new/";
};

const handleEditVehicle = (vehicle) => {
  window.location.href = `/vehicle/${vehicle.id}/edit/`;
};

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  return (
    <div className="vehicle-master">

      {/* HEADER */}
      <div className="vehicle-header">

        <div>
          <h2>Vehicle Master</h2>
          <p>Manage registered vehicles</p>
        </div>

        <button
          type="button"
          className="vehicle-add-btn"
          onClick={handleNewVehicle}
        >
          + New Vehicle
        </button>

      </div>

      {/* ERROR */}
      {error && (
        <div className="vehicle-alert">
          {error}
        </div>
      )}

      {/* SEARCH */}
      <div className="vehicle-search-wrapper">

        <input
          type="text"
          className="vehicle-search"
          placeholder="Search vehicle, customer, chassis, model..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {search && (
          <button
            type="button"
            className="vehicle-search-clear"
            onClick={() => setSearch("")}
          >
            ×
          </button>
        )}

      </div>

      {/* TABLE */}
      {loading ? (
        <div className="vehicle-loading">
          Loading vehicles...
        </div>
      ) : (
        <div className="vehicle-table-wrapper">

          <table className="vehicle-table">

            <thead>
              <tr>
                <th>Registration</th>
                <th>Chassis</th>
                <th>Engine</th>
                <th>Model</th>
                <th>Variant</th>
                <th>Color</th>
                <th>Customer</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>

              {filteredVehicles.length === 0 ? (
                <tr>
                  <td
                    colSpan="8"
                    className="vehicle-empty"
                  >
                    {search
                      ? "No vehicles match your search."
                      : "No vehicles found."}
                  </td>
                </tr>
              ) : (
                filteredVehicles.map((vehicle) => (
                  <tr key={vehicle.id}>

                    <td className="vehicle-registration">
                      {vehicle.registration_no || "-"}
                    </td>

                    <td>
                      {vehicle.chassis_no || "-"}
                    </td>

                    <td>
                      {vehicle.engine_no || "-"}
                    </td>

                    <td>
                      {vehicle.model__name || "-"}
                    </td>

                    <td>
                      {vehicle.variant__name || "-"}
                    </td>

                    <td>
                      {vehicle.color || "-"}
                    </td>

                    <td>
                      {vehicle.customer__name || "-"}
                    </td>

                    <td>
                      <button
                        type="button"
                        className="vehicle-edit-btn"
                        onClick={() => handleEditVehicle(vehicle)}
                      >
                        Edit
                      </button>
                    </td>

                  </tr>
                ))
              )}

            </tbody>

          </table>

        </div>
      )}

      {/* RESULT COUNT */}
      {!loading && vehicles.length > 0 && (
        <div className="vehicle-result-count">
          Showing {filteredVehicles.length} of {vehicles.length} vehicles
        </div>
      )}

    </div>
  );
}

export default VehicleMaster;