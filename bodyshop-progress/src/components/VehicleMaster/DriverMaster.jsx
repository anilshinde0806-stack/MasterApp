import { getCSRFToken } from "../../utils/csrf";
import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowLeftRight,
  Ban,
  CalendarDays,
  CarFront,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Edit3,
  FileText,
  Mail,
  MoreVertical,
  Phone,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  Upload,
  UserRound,
  UserRoundPlus,
  Users,
  X,
} from "lucide-react";
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

function getDriverType(driver) {
  return driver.type || driver.driver_type || "SELF";
}

function getDriverMobile(driver) {
  return driver.mobile || driver.mobile_no || "";
}

function getDriverLicense(driver) {
  return driver.driving_license_no || driver.license_no || "";
}

function getDriverValidUntil(driver) {
  return driver.valid_until || driver.license_valid_until || "";
}

function isDriverActive(driver) {
  if (typeof driver.is_active === "boolean") return driver.is_active;
  if (typeof driver.active === "boolean") return driver.active;
  if (typeof driver.status === "string") {
    return !["inactive", "disabled", "deactivated"].includes(
      driver.status.toLowerCase()
    );
  }
  return true;
}

function getAssignedVehicles(driver) {
  if (Array.isArray(driver.vehicles)) return driver.vehicles;
  if (Array.isArray(driver.assigned_vehicles)) return driver.assigned_vehicles;
  if (Array.isArray(driver.vehicle_list)) return driver.vehicle_list;

  if (driver.vehicle && typeof driver.vehicle === "object") {
    return [driver.vehicle];
  }

  if (driver.vehicle) {
    return [{ registration_no: driver.vehicle }];
  }

  return [];
}

function getVehicleLabel(vehicle) {
  if (!vehicle) return "-";
  if (typeof vehicle === "string") return vehicle;

  return (
    vehicle.registration_no ||
    vehicle.registration_number ||
    vehicle.vehicle_no ||
    vehicle.name ||
    "-"
  );
}

function formatDriverType(type) {
  const value = String(type || "").toUpperCase();

  if (value === "PAID") return "Paid Driver";
  if (value === "RELATIVE") return "Relative";
  return "Self";
}

function formatDate(value) {
  if (!value) return "-";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function DriverMaster() {
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const [search, setSearch] = useState("");
  const [driverTypeFilter, setDriverTypeFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedDriverId, setSelectedDriverId] = useState(null);

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

      const nextDrivers = Array.isArray(data.drivers) ? data.drivers : [];
      setDrivers(nextDrivers);
      setVehicles(Array.isArray(data.vehicles) ? data.vehicles : []);

      if (nextDrivers.length && selectedDriverId === null) {
        setSelectedDriverId(nextDrivers[0].id);
      }
    } catch (err) {
      console.error("Driver API error:", err);
      setError("Unable to load drivers.");
    } finally {
      setLoading(false);
    }
  }

  function handleNewDriver() {
    setError("");
    setForm(emptyForm);
    setShowForm(true);
  }

  function handleCancel() {
    setForm(emptyForm);
    setShowForm(false);
    setError("");
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
      setSaving(true);
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
              fieldErrors.map((fieldError) =>
                `${field}: ${fieldError.message}`
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
    } finally {
      setSaving(false);
    }
  }

  const filteredDrivers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return drivers.filter((driver) => {
      const name = String(driver.name || "").toLowerCase();
      const mobile = String(getDriverMobile(driver)).toLowerCase();
      const license = String(getDriverLicense(driver)).toLowerCase();
      const type = getDriverType(driver).toLowerCase();
      const active = isDriverActive(driver);

      const matchesSearch =
        !query ||
        name.includes(query) ||
        mobile.includes(query) ||
        license.includes(query);

      const matchesType =
        driverTypeFilter === "ALL" ||
        type === driverTypeFilter.toLowerCase();

      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && active) ||
        (statusFilter === "INACTIVE" && !active);

      return matchesSearch && matchesType && matchesStatus;
    });
  }, [drivers, search, driverTypeFilter, statusFilter]);

  const activeDrivers = drivers.filter(isDriverActive);
  const inactiveDrivers = drivers.filter((driver) => !isDriverActive(driver));
  const assignedVehicleCount = drivers.reduce(
    (total, driver) => total + getAssignedVehicles(driver).length,
    0
  );

  const selectedDriver =
    drivers.find((driver) => driver.id === selectedDriverId) ||
    filteredDrivers[0] ||
    drivers[0] ||
    null;

  const selectedVehicles = selectedDriver
    ? getAssignedVehicles(selectedDriver)
    : [];

  function selectDriver(driver) {
    setSelectedDriverId(driver.id);
  }

  return (
    <div className="driver-master-page">
      <div className="driver-master-breadcrumb">
        <span className="driver-master-breadcrumb-home">⌂</span>
        <span>›</span>
        <span>Driver Master</span>
      </div>

      <header className="driver-master-header">
        <div className="driver-master-title-wrap">
          <div className="driver-master-title-icon">
            <Users size={25} strokeWidth={2.2} />
          </div>

          <div>
            <h1>Driver Master</h1>
            <p>Manage your drivers and their assignments</p>
          </div>
        </div>

        <button
          type="button"
          className="driver-master-primary-btn"
          onClick={handleNewDriver}
        >
          <Plus size={17} />
          Add Driver
        </button>
      </header>

      {error && (
        <div className="driver-master-error">
          <span>{error}</span>
          <button type="button" onClick={() => setError("")}>
            <X size={16} />
          </button>
        </div>
      )}

      {showForm ? (
        <section className="driver-master-form-card">
          <div className="driver-master-form-header">
            <div>
              <h2>New Driver</h2>
              <p>Enter driver identity, licence and vehicle assignment details.</p>
            </div>

            <button
              type="button"
              className="driver-master-icon-btn"
              onClick={handleCancel}
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>

          <div className="driver-master-form-grid">
            <div className="driver-master-field">
              <label>Driver Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(event) =>
                  updateField("name", event.target.value)
                }
                placeholder="Enter driver name"
              />
            </div>

            <div className="driver-master-field">
              <label>Driver Type</label>
              <select
                value={form.driver_type}
                onChange={(event) =>
                  updateField("driver_type", event.target.value)
                }
              >
                <option value="SELF">Self</option>
                <option value="PAID">Paid Driver</option>
                <option value="RELATIVE">Relative</option>
              </select>
            </div>

            <div className="driver-master-field">
              <label>Mobile No.</label>
              <input
                type="text"
                value={form.mobile_no}
                onChange={(event) =>
                  updateField("mobile_no", event.target.value)
                }
                placeholder="Enter mobile number"
              />
            </div>

            <div className="driver-master-field">
              <label>Driving Licence No. *</label>
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

            <div className="driver-master-field">
              <label>Licence Valid Until</label>
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

            <div className="driver-master-field">
              <label>Assign Vehicle</label>
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

            <div className="driver-master-upload-field">
              <div className="driver-master-upload-icon">
                <Upload size={18} />
              </div>
              <div>
                <label>Face Photo</label>
                <p>
                  {form.face_photo?.name || "Upload driver photo"}
                </p>
              </div>
              <input
                type="file"
                accept="image/*"
                onChange={(event) =>
                  handleFileChange("face_photo", event)
                }
              />
            </div>

            <div className="driver-master-upload-field">
              <div className="driver-master-upload-icon">
                <FileText size={18} />
              </div>
              <div>
                <label>Licence Document</label>
                <p>
                  {form.license_document?.name ||
                    "Upload licence document"}
                </p>
              </div>
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

          <div className="driver-master-form-actions">
            <button
              type="button"
              className="driver-master-secondary-btn"
              onClick={handleCancel}
            >
              Cancel
            </button>

            <button
              type="button"
              className="driver-master-primary-btn"
              onClick={handleSaveDriver}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Driver"}
            </button>
          </div>
        </section>
      ) : (
        <>
          <section className="driver-master-toolbar">
            <div className="driver-master-search-wrap">
              <Search size={18} />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by name, mobile, licence no..."
              />
            </div>

            <select
              value={driverTypeFilter}
              onChange={(event) =>
                setDriverTypeFilter(event.target.value)
              }
            >
              <option value="ALL">Driver Type · All</option>
              <option value="SELF">Self</option>
              <option value="PAID">Paid Driver</option>
              <option value="RELATIVE">Relative</option>
            </select>

            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value)
              }
            >
              <option value="ALL">Status · All</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>

            <button
              type="button"
              className="driver-master-reset-btn"
              onClick={() => {
                setSearch("");
                setDriverTypeFilter("ALL");
                setStatusFilter("ALL");
              }}
              title="Reset filters"
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </section>

          <section className="driver-master-stat-grid">
            <div className="driver-master-stat-card">
              <div className="driver-master-stat-icon blue">
                <Users size={21} />
              </div>
              <div>
                <span>Total Drivers</span>
                <strong>{drivers.length}</strong>
                <small>Registered drivers</small>
              </div>
            </div>

            <div className="driver-master-stat-card">
              <div className="driver-master-stat-icon green">
                <CheckCircle2 size={21} />
              </div>
              <div>
                <span>Active Drivers</span>
                <strong>{activeDrivers.length}</strong>
                <small>
                  {drivers.length
                    ? Math.round(
                        (activeDrivers.length / drivers.length) * 100
                      )
                    : 0}
                  % of total
                </small>
              </div>
            </div>

            <div className="driver-master-stat-card">
              <div className="driver-master-stat-icon orange">
                <UserRound size={21} />
              </div>
              <div>
                <span>Inactive Drivers</span>
                <strong>{inactiveDrivers.length}</strong>
                <small>Need attention</small>
              </div>
            </div>

            <div className="driver-master-stat-card">
              <div className="driver-master-stat-icon blue">
                <CarFront size={21} />
              </div>
              <div>
                <span>Assigned Vehicles</span>
                <strong>{assignedVehicleCount}</strong>
                <small>Current assignments</small>
              </div>
            </div>
          </section>

          <section className="driver-master-content">
            <div className="driver-master-list-card">
              <div className="driver-master-list-header">
                <div>
                  <h2>Registered Drivers</h2>
                  <p>
                    Showing {filteredDrivers.length} of{" "}
                    {drivers.length} drivers
                  </p>
                </div>
              </div>

              {loading ? (
                <div className="driver-master-loading">
                  Loading drivers...
                </div>
              ) : filteredDrivers.length === 0 ? (
                <div className="driver-master-empty">
                  <Users size={34} />
                  <strong>No drivers found</strong>
                  <span>Try changing your search or filters.</span>
                </div>
              ) : (
                <div className="driver-master-table-wrapper">
                  <table className="driver-master-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Driver Name</th>
                        <th>Mobile</th>
                        <th>Licence No.</th>
                        <th>Licence Expiry</th>
                        <th>Driver Type</th>
                        <th>Status</th>
                        <th>Assigned Vehicles</th>
                        <th>Actions</th>
                      </tr>
                    </thead>

                    <tbody>
                      {filteredDrivers.map((driver, index) => {
                        const active = isDriverActive(driver);
                        const assignedVehicles =
                          getAssignedVehicles(driver);

                        return (
                          <tr
                            key={driver.id}
                            className={
                              selectedDriver?.id === driver.id
                                ? "selected"
                                : ""
                            }
                            onClick={() => selectDriver(driver)}
                          >
                            <td className="driver-master-index">
                              {index + 1}
                            </td>

                            <td>
                              <div className="driver-master-name-cell">
                                {driver.photo ? (
                                  <img
                                    src={driver.photo}
                                    alt={driver.name}
                                    className="driver-master-photo"
                                  />
                                ) : (
                                  <div className="driver-master-photo-placeholder">
                                    <UserRound size={18} />
                                  </div>
                                )}

                                <div>
                                  <strong>{driver.name}</strong>
                                  {driver.primary && (
                                    <span className="driver-master-primary-tag">
                                      Primary
                                    </span>
                                  )}
                                </div>
                              </div>
                            </td>

                            <td>
                              <span className="driver-master-mobile">
                                <Phone size={13} />
                                {getDriverMobile(driver) || "-"}
                              </span>
                            </td>

                            <td className="driver-master-license">
                              {getDriverLicense(driver) || "-"}
                            </td>

                            <td>
                              {formatDate(getDriverValidUntil(driver))}
                            </td>

                            <td>
                              <span className="driver-master-type-pill">
                                {formatDriverType(
                                  getDriverType(driver)
                                )}
                              </span>
                            </td>

                            <td>
                              <span
                                className={`driver-master-status ${
                                  active ? "active" : "inactive"
                                }`}
                              >
                                <span />
                                {active ? "Active" : "Inactive"}
                              </span>
                            </td>

                            <td>
                              {assignedVehicles.length ? (
                                <div className="driver-master-assigned">
                                  <CarFront size={15} />
                                  <span>
                                    {assignedVehicles.length}
                                  </span>
                                </div>
                              ) : (
                                <span className="driver-master-no-assignment">
                                  0
                                </span>
                              )}
                            </td>

                            <td>
                              <button
                                type="button"
                                className="driver-master-more-btn"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  selectDriver(driver);
                                }}
                                aria-label={`Actions for ${driver.name}`}
                              >
                                <MoreVertical size={18} />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="driver-master-pagination">
                <span>
                  Showing 1–{filteredDrivers.length} of{" "}
                  {drivers.length}
                </span>

                <div>
                  <button type="button" disabled>
                    <ChevronLeft size={16} />
                  </button>
                  <button type="button" className="current">
                    1
                  </button>
                  <button type="button" disabled>
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>

            {selectedDriver && (
              <aside className="driver-master-details-card">
                <div className="driver-master-details-header">
                  <div>
                    <h2>Driver Details</h2>
                    <p>Profile and assignment information</p>
                  </div>

                  <button
                    type="button"
                    className="driver-master-icon-btn"
                    onClick={() => setSelectedDriverId(null)}
                  >
                    <X size={17} />
                  </button>
                </div>

                <div className="driver-master-profile">
                  {selectedDriver.photo ? (
                    <img
                      src={selectedDriver.photo}
                      alt={selectedDriver.name}
                      className="driver-master-profile-photo"
                    />
                  ) : (
                    <div className="driver-master-profile-placeholder">
                      <UserRound size={28} />
                    </div>
                  )}

                  <div className="driver-master-profile-main">
                    <h3>{selectedDriver.name}</h3>
                    <span>
                      {isDriverActive(selectedDriver)
                        ? "Active"
                        : "Inactive"}
                    </span>
                    <small>
                      {selectedDriver.primary
                        ? "Primary Driver"
                        : formatDriverType(
                            getDriverType(selectedDriver)
                          )}
                    </small>
                  </div>
                </div>

                <div className="driver-master-contact-row">
                  <a
                    href={
                      getDriverMobile(selectedDriver)
                        ? `tel:${getDriverMobile(selectedDriver)}`
                        : undefined
                    }
                  >
                    <Phone size={15} />
                    {getDriverMobile(selectedDriver) || "-"}
                  </a>

                  {selectedDriver.email && (
                    <a href={`mailto:${selectedDriver.email}`}>
                      <Mail size={15} />
                      {selectedDriver.email}
                    </a>
                  )}
                </div>

                <div className="driver-master-detail-tabs">
                  <button type="button" className="active">
                    Profile
                  </button>
                  <button type="button">
                    Assigned Vehicles ({selectedVehicles.length})
                  </button>
                  <button type="button">Documents</button>
                </div>

                <div className="driver-master-detail-section">
                  <div className="driver-master-section-title">
                    <UserRound size={16} />
                    Personal Information
                  </div>

                  <div className="driver-master-detail-grid">
                    <span>Full Name</span>
                    <strong>{selectedDriver.name || "-"}</strong>

                    <span>Mobile No.</span>
                    <strong>
                      {getDriverMobile(selectedDriver) || "-"}
                    </strong>

                    <span>Driver Type</span>
                    <strong>
                      {formatDriverType(
                        getDriverType(selectedDriver)
                      )}
                    </strong>

                    <span>Address</span>
                    <strong>
                      {selectedDriver.address || "-"}
                    </strong>
                  </div>
                </div>

                <div className="driver-master-detail-section">
                  <div className="driver-master-section-title">
                    <ShieldCheck size={16} />
                    Licence Information
                  </div>

                  <div className="driver-master-detail-grid">
                    <span>Licence No.</span>
                    <strong>
                      {getDriverLicense(selectedDriver) || "-"}
                    </strong>

                    <span>Expiry Date</span>
                    <strong>
                      {formatDate(
                        getDriverValidUntil(selectedDriver)
                      )}
                    </strong>

                    <span>Licence Document</span>
                    <strong>
                      {selectedDriver.documents ? (
                        <a
                          href={selectedDriver.documents}
                          target="_blank"
                          rel="noreferrer"
                          className="driver-master-document-link"
                        >
                          View Document
                        </a>
                      ) : (
                        "-"
                      )}
                    </strong>
                  </div>
                </div>

                <div className="driver-master-detail-section">
                  <div className="driver-master-section-title">
                    <CarFront size={16} />
                    Assigned Vehicles
                  </div>

                  {selectedVehicles.length ? (
                    <div className="driver-master-vehicle-list">
                      {selectedVehicles.map((vehicle, vehicleIndex) => (
                        <div
                          className="driver-master-vehicle-item"
                          key={
                            vehicle.id ||
                            `${getVehicleLabel(vehicle)}-${vehicleIndex}`
                          }
                        >
                          <div>
                            <CarFront size={16} />
                          </div>
                          <span>
                            <strong>
                              {getVehicleLabel(vehicle)}
                            </strong>
                            <small>
                              {vehicle.model__name ||
                                vehicle.model ||
                                vehicle.model_name ||
                                "Assigned Vehicle"}
                            </small>
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="driver-master-no-vehicle-box">
                      <CarFront size={18} />
                      <span>No vehicle assigned</span>
                    </div>
                  )}
                </div>

                <div className="driver-master-detail-actions">
                  <button type="button" className="driver-master-edit-btn">
                    <Edit3 size={15} />
                    Edit
                  </button>

                  <button
                    type="button"
                    className="driver-master-change-btn"
                  >
                    <ArrowLeftRight size={15} />
                    Change Assignment
                  </button>

                  <button
                    type="button"
                    className="driver-master-deactivate-btn"
                  >
                    <Ban size={15} />
                    {isDriverActive(selectedDriver)
                      ? "Deactivate"
                      : "Activate"}
                  </button>
                </div>
              </aside>
            )}
          </section>
        </>
      )}
    </div>
  );
}
