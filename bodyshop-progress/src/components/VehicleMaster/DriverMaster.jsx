import { getCSRFToken } from "../../utils/csrf";
import React, { useEffect, useState } from "react";
import "./DriverMaster.css";

const emptyForm = {
  id: "",
  name: "",
  vehicle: "",
  driver_type: "SELF",
  mobile_no: "",
  driving_license_no: "",
  license_valid_until: "",
  license_document: null,
  face_photo: null,
};

export default function DriverMaster() {
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    loadDrivers();
  }, []);

  async function loadDrivers() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("/ajax/vehicle-form-data/", {
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

setDrivers(
  Array.isArray(data.drivers)
    ? data.drivers
    : []
);

setVehicles(
  Array.isArray(data.vehicles)
    ? data.vehicles
    : []
);
    } catch (err) {
      console.error("Driver API error:", err);
      setError("Unable to load drivers.");
    } finally {
      setLoading(false);
    }
  }

  function handleNewDriver() {
    setForm(emptyForm);
    setShowForm(true);
  }

  function handleCancel() {
    setForm(emptyForm);
    setShowForm(false);
  }

  function updateField(field, value) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  }

  function handleFileChange(field, event) {
    const file = event.target.files?.[0] || null;

    setForm((previous) => ({
      ...previous,
      [field]: file,
    }));
  }
  async function handleSaveDriver() {
  try {
    setError("");

    if (!form.name.trim()) {
      setError("Driver name is required.");
      return;
    }

    if (!form.driving_license_no.trim()) {
      setError("Driving Licence No. is required.");
      return;
    }

    const formData = new FormData();

    formData.append("name", form.name);
    formData.append("driver_type", form.driver_type);
    formData.append("mobile_no", form.mobile_no);
    formData.append(
      "driving_license_no",
      form.driving_license_no
    );

    if (form.license_valid_until) {
      formData.append(
        "license_valid_until",
        form.license_valid_until
      );
    }

    if (form.vehicle) {
      formData.append("vehicle", form.vehicle);
    }

    if (form.face_photo) {
      formData.append("face_photo", form.face_photo);
    }

    if (form.license_document) {
      formData.append(
        "license_document",
        form.license_document
      );
    }

   const response = await fetch("/ajax/driver-master/save/", {
  method: "POST",
  credentials: "same-origin",
  headers: {
    "X-CSRFToken": getCSRFToken(),
  },
  body: formData,
});


    const data = await response.json();

if (!response.ok || !data.success) {
  console.error("Driver save error:", data);

  const errors = data.errors;

  if (errors) {
    const messages = Object.entries(errors)
      .flatMap(([field, fieldErrors]) =>
        fieldErrors.map((error) =>
          `${field}: ${error.message}`
        )
      )
      .join("\n");

    setError(messages || "Unable to save driver.");
  } else {
    setError(data.error || "Unable to save driver.");
  }

  return;
}

    setForm(emptyForm);
    setShowForm(false);

    await loadDrivers();
  } catch (err) {
    console.error("Save driver error:", err);
    setError("Unable to save driver.");
  }
}
  return (
    <div className="driver-master-page">

      {/* HEADER */}
      <div className="driver-master-header">

        <div>
          <h2>Driver Master</h2>

          <p>
            Manage driver identity and licence documents
          </p>
        </div>

        {!showForm && (
          <button
            type="button"
            className="driver-master-new-btn"
            onClick={handleNewDriver}
          >
            + New Driver
          </button>
        )}

      </div>


      {/* NEW DRIVER FORM */}
      {showForm && (
        <section className="driver-master-form-card">

          <div className="driver-master-section-header">

            <div>
              <h3>New Driver</h3>

              <p>
                Enter driver information
              </p>
            </div>

            <button
              type="button"
              className="driver-master-cancel-btn"
              onClick={handleCancel}
            >
              Cancel
            </button>

          </div>


          <div className="driver-master-form-grid">

            {/* NAME */}
            <div className="driver-master-field">
              <label>Driver Name</label>

              <input
                type="text"
                value={form.name}
                onChange={(event) =>
                  updateField("name", event.target.value)
                }
                placeholder="Enter driver name"
              />
            </div>


            {/* DRIVER TYPE */}
            <div className="driver-master-field">
              <label>Driver Type</label>

              <select
                value={form.driver_type}
                onChange={(event) =>
                  updateField(
                    "driver_type",
                    event.target.value
                  )
                }
              >
                <option value="SELF">Self</option>
                <option value="PAID">Paid Driver</option>
                <option value="RELATIVE">Relative</option>
              </select>
            </div>


            {/* MOBILE */}
            <div className="driver-master-field">
              <label>Mobile No.</label>

              <input
                type="text"
                value={form.mobile_no}
                onChange={(event) =>
                  updateField(
                    "mobile_no",
                    event.target.value
                  )
                }
                placeholder="Enter mobile number"
              />
            </div>


            {/* LICENSE */}
            <div className="driver-master-field">
              <label>Driving Licence No.</label>

              <input
                type="text"
                value={form.driving_license_no}
                onChange={(event) =>
                  updateField(
                    "driving_license_no",
                    event.target.value
                  )
                }
                placeholder="Enter licence number"
              />
            </div>


            {/* VALID UNTIL */}
            <div className="driver-master-field">
              <label>Valid Until</label>

              <input
                type="date"
                value={form.license_valid_until}
                onChange={(event) =>
                  updateField(
                    "license_valid_until",
                    event.target.value
                  )
                }
              />
            </div>


            {/* VEHICLE */}
            <div className="driver-master-field">
              <label>Vehicle</label>

              <select
  value={form.vehicle}
  onChange={(event) =>
    updateField("vehicle", event.target.value)
  }
>
  <option value="">Select Vehicle</option>

  {vehicles.map((vehicle) => (
    <option key={vehicle.id} value={vehicle.id}>
      {vehicle.registration_no}
      {vehicle.model__name
        ? ` · ${vehicle.model__name}`
        : ""}
      {vehicle.variant__name
        ? ` · ${vehicle.variant__name}`
        : ""}
    </option>
  ))}
</select>
            </div>


            {/* FACE PHOTO */}
            <div className="driver-master-field">
              <label>Face Photo</label>

              <input
                type="file"
                accept="image/*"
                onChange={(event) =>
                  handleFileChange(
                    "face_photo",
                    event
                  )
                }
              />
            </div>


            {/* LICENSE DOCUMENT */}
            <div className="driver-master-field">
              <label>Licence Document</label>

              <input
                type="file"
                onChange={(event) =>
                  handleFileChange(
                    "license_document",
                    event
                  )
                }
              />
            </div>

          </div>


          {/* FORM ACTIONS */}
          <div className="driver-master-form-actions">

            <button
              type="button"
              className="driver-master-cancel-btn"
              onClick={handleCancel}
            >
              Cancel
            </button>

            <button
  type="button"
  className="driver-master-save-btn"
  onClick={handleSaveDriver}
>
  Save Driver
</button>

          </div>

        </section>
      )}


      {/* ERROR */}
      {error && (
        <div className="driver-master-error">
          {error}
        </div>
      )}


      {/* DRIVER LIST */}
      {!showForm && (
        <section className="driver-master-list-card">

          <div className="driver-master-list-header">
            <h3>Registered Drivers</h3>
          </div>

          {loading ? (
            <div className="driver-master-loading">
              Loading drivers...
            </div>
          ) : (
            <div className="driver-master-table-wrapper">

              <table className="driver-master-table">

                <thead>
                  <tr>
                    <th>Select One</th>
                    <th>Photo</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Mobile</th>
                    <th>Driving Licence No.</th>
                    <th>Valid Until</th>
                    <th>Documents</th>
                  </tr>
                </thead>

                <tbody>

                  {drivers.length === 0 ? (
                    <tr>
                      <td
                        colSpan="8"
                        className="driver-master-empty"
                      >
                        No drivers registered.
                      </td>
                    </tr>
                  ) : (
                    drivers.map((driver) => (
                      <tr key={driver.id}>

                        <td>
                          <input
                            type="radio"
                            name="selected_driver"
                            value={driver.id}
                          />
                        </td>

                        <td>
                          {driver.photo ? (
                            <img
                              src={driver.photo}
                              alt={driver.name}
                              className="driver-master-photo"
                            />
                          ) : (
                            <div className="driver-master-photo-placeholder">
                              👤
                            </div>
                          )}
                        </td>

                        <td>
                          <strong>
                            {driver.name}
                          </strong>
                        </td>

                        <td>
                          {driver.type ||
                            driver.driver_type ||
                            "-"}
                        </td>

                        <td>
                          {driver.mobile || "-"}
                        </td>

                        <td>
                          {driver.driving_license_no ||
                            "-"}
                        </td>

                        <td>
                          {driver.valid_until || "-"}
                        </td>

                        <td>
                          {driver.documents ? (
                            <a
                              href={driver.documents}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Licence
                            </a>
                          ) : (
                            "-"
                          )}
                        </td>

                      </tr>
                    ))
                  )}

                </tbody>

              </table>

            </div>
          )}

        </section>
      )}

    </div>
  );
}