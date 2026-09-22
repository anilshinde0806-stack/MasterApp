import { useEffect, useState } from "react";
import "./VehicleMasterView.css";

function VehicleMasterView() {
  const [vehicle, setVehicle] = useState(null);
  const [formData, setFormData] = useState(null);
  const [activeTab, setActiveTab] = useState("basic");
  const [selectedImage, setSelectedImage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const path = window.location.pathname;
  const match = path.match(/^\/vehicle\/(\d+)\/$/);
  const vehicleId = match ? match[1] : null;

  useEffect(() => {
    const loadVehicle = async () => {
      if (!vehicleId) {
        setError("Invalid vehicle.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const [vehicleResponse, formResponse] = await Promise.all([
          fetch(`/ajax/vehicle/${vehicleId}/`, {
            credentials: "same-origin",
          }),
          fetch("/ajax/vehicle-form-data/", {
            credentials: "same-origin",
          }),
        ]);

        if (!vehicleResponse.ok) {
          throw new Error(`Vehicle HTTP ${vehicleResponse.status}`);
        }

        if (!formResponse.ok) {
          throw new Error(`Form HTTP ${formResponse.status}`);
        }

        const vehicleData = await vehicleResponse.json();
        const optionsData = await formResponse.json();

        setVehicle(vehicleData);
        setFormData(optionsData);
      } catch (err) {
        console.error("Vehicle view error:", err);
        setError("Unable to load vehicle details.");
      } finally {
        setLoading(false);
      }
    };

    loadVehicle();
  }, [vehicleId]);

  const getModelName = () => {
    if (!vehicle || !formData) return "-";

    const model = (formData.models || []).find(
      (item) => String(item.id) === String(vehicle.model)
    );

    return model?.name || "-";
  };

  const getVariantName = () => {
    if (!vehicle || !formData) return "-";

    const variant = (formData.variants || []).find(
      (item) => String(item.id) === String(vehicle.variant)
    );

    return variant?.name || "-";
  };

  const getVehicleTypeName = () => {
    if (!vehicle) return "-";

    if (!formData) {
      return vehicle.id_vehicle_type || "-";
    }

    const type = (formData.vehicle_types || []).find(
      (item) =>
        String(item.id) === String(vehicle.id_vehicle_type) ||
        String(item.value) === String(vehicle.id_vehicle_type)
    );

    return (
      type?.name ||
      type?.label ||
      vehicle.id_vehicle_type ||
      "-"
    );
  };

  const getColorName = () => {
    if (!vehicle) return "-";

    if (!formData) {
      return vehicle.id_color || "-";
    }

    const color = (formData.colors || []).find(
      (item) =>
        String(item.id) === String(vehicle.id_color) ||
        String(item.value) === String(vehicle.id_color)
    );

    return color?.name || color?.label || vehicle.id_color || "-";
  };

  const formatValue = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "Not Added";
    }

    return value;
  };

  const handleBack = () => {
    window.location.href = "/vehicle/";
  };

  const handleEdit = () => {
    window.location.href = `/vehicle/${vehicleId}/edit/`;
  };

  if (loading) {
    return (
      <div className="vehicle-view-page">
        <div className="vehicle-view-loading">
          Loading vehicle details...
        </div>
      </div>
    );
  }

  if (error || !vehicle) {
    return (
      <div className="vehicle-view-page">
        <div className="vehicle-view-error">
          {error || "Vehicle not found."}
        </div>
      </div>
    );
  }

  const vehicleName =
    vehicle.vehicle_name ||
    getVariantName() ||
    getModelName() ||
    vehicle.registration_no ||
    "Vehicle";

  const modelName = getModelName();
  const variantName = getVariantName();
  const vehicleType = getVehicleTypeName();
  const colorName = getColorName();

  return (
    <div className="vehicle-view-page">
      <div className="vehicle-view-container">

        {/* =====================================================
            PAGE HEADER
        ===================================================== */}
        <div className="vehicle-view-topbar">
          <div className="vehicle-view-title-area">
            <button
              type="button"
              className="vehicle-view-back-btn"
              onClick={handleBack}
              title="Back"
            >
              ←
            </button>

            <h1>{vehicleName}</h1>
          </div>

          <div className="vehicle-view-actions">
            <button type="button" title="Add">
              +
            </button>

            <button type="button" title="Settings">
              ⚙
            </button>

            <button
              type="button"
              className="vehicle-view-edit-btn"
              onClick={handleEdit}
              title="Edit Vehicle"
            >
              ✎
            </button>
          </div>
        </div>


        {/* =====================================================
            HERO
        ===================================================== */}
        <section className="vehicle-view-hero">

          <div className="vehicle-view-hero-image">
            {vehicle.vehicle_image ? (
              <img src={vehicle.vehicle_image} alt={vehicleName} className="vehicle-view-hero-photo" />
            ) : <div className="vehicle-view-car-placeholder">🚗</div>}
          </div>

          <div className="vehicle-view-hero-details">
            <div className="vehicle-view-hero-title-row">
              <h2>{vehicleName}</h2>

              <button
                type="button"
                className="vehicle-view-small-edit"
                onClick={handleEdit}
                title="Edit"
              >
                ✎
              </button>
            </div>

            <div className="vehicle-view-hero-meta">
              <span>
                🚗 {formatValue(vehicleType)}
              </span>

              <span>
                📅 {formatValue(vehicle.sale_date)}
              </span>
            </div>

            <div className="vehicle-view-hero-km">
              ◉ {formatValue(vehicle.last_service_km)} km
            </div>
          </div>

          <div className="vehicle-view-decoration">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
        </section>


        {/* =====================================================
            TABS
        ===================================================== */}
        <div className="vehicle-view-tabs">
          <button
            type="button"
            className={activeTab === "basic" ? "active" : ""}
            onClick={() => setActiveTab("basic")}
          >
            BASIC DETAILS
          </button>

          <button
            type="button"
            className={activeTab === "description" ? "active" : ""}
            onClick={() => setActiveTab("description")}
          >
            DESCRIPTION
          </button>

          <button
            type="button"
            className={activeTab === "maintenance" ? "active" : ""}
            onClick={() => setActiveTab("maintenance")}
          >
            MAINTENANCE HISTORY
          </button>

          <button
            type="button"
            className={activeTab === "notes" ? "active" : ""}
            onClick={() => setActiveTab("notes")}
          >
            NOTES
          </button>
        </div>


        {/* =====================================================
            BASIC DETAILS
        ===================================================== */}
        {activeTab === "basic" && (
          <>
            <div className="vehicle-view-summary">

              <div className="vehicle-view-summary-item">
                <span>NUMBER PLATE</span>
                <strong>
                  {formatValue(vehicle.registration_no)}
                </strong>
              </div>

              <div className="vehicle-view-summary-item">
                <span>VEHICLE NAME</span>
                <strong>{vehicleName}</strong>
              </div>

              <div className="vehicle-view-summary-item">
                <span>DATE OF SALE</span>
                <strong>
                  {formatValue(vehicle.sale_date)}
                </strong>
              </div>

              <div className="vehicle-view-summary-item">
                <span>VEHICLE TYPE</span>
                <strong>{formatValue(vehicleType)}</strong>
              </div>

            </div>


            {/* =================================================
                MAIN INFORMATION
            ================================================= */}
            <div className="vehicle-view-content">

              {/* IMAGE CARD */}
              <div className="vehicle-view-image-card">

                <div className="vehicle-view-main-image">
                  {vehicle.vehicle_image ? (
                    <img src={vehicle.vehicle_image} alt={vehicleName} className="vehicle-view-large-photo" />
                  ) : <div className="vehicle-view-large-car">🚗</div>}
                </div>

                <div className="vehicle-view-thumbnails">

                  <button type="button" className="active" onClick={() => setSelectedImage(0)}>
                    {vehicle.vehicle_image ? <img src={vehicle.vehicle_image} alt="Vehicle thumbnail" /> : "🚗"}
                  </button>

                </div>
              </div>


              {/* MORE INFO */}
              <div className="vehicle-view-info-card">

                <h2>More Info.</h2>

                <div className="vehicle-view-info-grid">

                  <div className="vehicle-view-info-item">
                    <span>VEHICLE MODEL</span>
                    <strong>{formatValue(modelName)}</strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>VARIANT</span>
                    <strong>{formatValue(variantName)}</strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>CHASSIS NO</span>
                    <strong>
                      {formatValue(vehicle.id_chassis_no)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>ENGINE NO</span>
                    <strong>
                      {formatValue(vehicle.id_engine_no)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>NUMBER PLATE</span>
                    <strong>
                      {formatValue(vehicle.registration_no)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>COLOR</span>
                    <strong className="vehicle-view-color-value">
                      <i
                        className="vehicle-view-color-dot"
                      ></i>
                      {formatValue(colorName)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>CUSTOMER</span>
                    <strong>
                      {formatValue(vehicle.customer_name)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>INSURANCE</span>
                    <strong>
                      {formatValue(
                        vehicle.insurance_company_name
                      )}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>POLICY NO</span>
                    <strong>
                      {formatValue(vehicle.policy_no)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>LAST SERVICE KM</span>
                    <strong>
                      {formatValue(vehicle.last_service_km)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>POLICY START DATE</span>
                    <strong>
                      {formatValue(vehicle.policy_start_date)}
                    </strong>
                  </div>

                  <div className="vehicle-view-info-item">
                    <span>POLICY END DATE</span>
                    <strong>
                      {formatValue(vehicle.policy_end_date)}
                    </strong>
                  </div>

                </div>
              </div>
            </div>
          </>
        )}


        {/* =====================================================
            DESCRIPTION
        ===================================================== */}
        {activeTab === "description" && (
          <div className="vehicle-view-tab-panel">
            <h2>Description</h2>
            <p>
              No vehicle description has been added.
            </p>
          </div>
        )}


        {/* =====================================================
            MAINTENANCE HISTORY
        ===================================================== */}
        {activeTab === "maintenance" && (
          <div className="vehicle-view-tab-panel">

            <h2>Maintenance History</h2>

            <div className="vehicle-view-maintenance-card">

              <div>
                <span>LAST SERVICE DATE</span>
                <strong>
                  {formatValue(vehicle.last_service_date)}
                </strong>
              </div>

              <div>
                <span>LAST SERVICE KM</span>
                <strong>
                  {formatValue(vehicle.last_service_km)}
                </strong>
              </div>

              <div>
                <span>SERVICE TYPE</span>
                <strong>
                  {formatValue(vehicle.last_service_type)}
                </strong>
              </div>

            </div>
          </div>
        )}


        {/* =====================================================
            NOTES
        ===================================================== */}
        {activeTab === "notes" && (
          <div className="vehicle-view-tab-panel">
            <h2>Notes</h2>
            <p>
              No notes have been added for this vehicle.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}

export default VehicleMasterView;
