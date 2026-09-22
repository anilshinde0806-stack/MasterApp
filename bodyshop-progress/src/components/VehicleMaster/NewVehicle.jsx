import { useEffect, useMemo, useRef, useState } from "react";
import "./NewVehicle.css";
import DriverAssignmentSection from "./DriverAssignmentSection";
const VEHICLE_NUMBER_PATTERN = /^([A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{1,4}|(22|23|24|25|26)[A-Z]{2}[0-9]{1,4}[A-Z]?)$/i;
const VEHICLE_NUMBER_ERROR = "Enter valid vehicle no. Example: GJ05AB1234 or 22BH1234A.";
const EMPTY_FORM = {
  registration_no: "",
  chassis_no: "",
  engine_no: "",
  vehicle_type: "",
  model: "",
  variant: "",
  color: "",
  customer: "",
  sale_date: "",
  insurance_company: "",
  policy_no: "",
  policy_start_date: "",
  policy_end_date: "",
  last_service_km: "",
  last_service_type: "",
  last_service_date: "",
  primary_driver: "",
  assigned_drivers: [],
  vehicle_image: null,
  rc_document: null,
  insurance_policy_document: null,
};

function NewVehicle() {
  // --------------------------------------------------
  // ADD / EDIT MODE
  // --------------------------------------------------

  const path = window.location.pathname;

  const editMatch = path.match(/^\/vehicle\/(\d+)\/edit\/$/);

  const vehicleId = editMatch ? editMatch[1] : null;

  const isEditMode = Boolean(vehicleId);

  // --------------------------------------------------
  // FORM
  // --------------------------------------------------

  const [form, setForm] = useState(EMPTY_FORM);

  const [customers, setCustomers] = useState([]);
  const [models, setModels] = useState([]);
  const [variants, setVariants] = useState([]);
  const [insuranceCompanies, setInsuranceCompanies] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [vehicleTypes, setVehicleTypes] = useState([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");
  const [formErrors, setFormErrors] = useState({});

  const [existingDocuments, setExistingDocuments] = useState({
    vehicle_image: "",
    rc_document: "",
    insurance_policy_document: "",
  });
  const [assignedDriverDetails, setAssignedDriverDetails] = useState([]);

  // --------------------------------------------------
  // MODEL / VARIANT MODALS
  // --------------------------------------------------

  const [showModelModal, setShowModelModal] = useState(false);
  const [showVariantModal, setShowVariantModal] = useState(false);
  const [newModelName, setNewModelName] = useState("");
  const [newVariantName, setNewVariantName] = useState("");
  const [modalError, setModalError] = useState("");
  const [modalSaving, setModalSaving] = useState(false);
  // --------------------------------------------------
  // LOAD FORM OPTIONS
  // --------------------------------------------------

  useEffect(() => {
    const loadOptions = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          "/ajax/vehicle-form-data/",
          {
            credentials: "same-origin",
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        //setAssignedDriverDetails(data.assigned_driver_details || []);
        setCustomers(data.customers || []);
        setModels(data.models || []);
        // Variants are loaded dynamically when a model is selected.
        setVariants([]);

        setInsuranceCompanies(
          (data.insurance_companies || []).map(
            (company) => ({
              value: company.id,
              label: company.ins_co_name,
            })
          )
        );

        setDrivers(data.drivers || []);
        setVehicleTypes(data.vehicle_types || []);
      } catch (err) {
        console.error(
          "Vehicle form data error:",
          err
        );

        setError(
          "Unable to load vehicle form data."
        );
      }
    };

    loadOptions();
  }, []);

  // --------------------------------------------------
  // LOAD EXISTING VEHICLE
  // --------------------------------------------------

  useEffect(() => {
    if (!vehicleId) {
      setLoading(false);
      return;
    }

    const loadVehicle = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(
          `/ajax/vehicle/${vehicleId}/`,
          {
            credentials: "same-origin",
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log("Vehicle data:", data);
        setAssignedDriverDetails(data.assigned_driver_details || []);

        if (data.model) {
          try {
            const variantResponse = await fetch(
              `/ajax/load-variants/?model_id=${data.model}`,
              { credentials: "same-origin" }
            );

            if (variantResponse.ok) {
              const variantData = await variantResponse.json();
              setVariants(variantData || []);
            }
          } catch (variantError) {
            console.error("Variant load error:", variantError);
            setVariants([]);
          }
        } else {
          setVariants([]);
        }

        setForm({
          registration_no:
            data.registration_no || "",

          chassis_no:
            data.id_chassis_no || "",

          engine_no:
            data.id_engine_no || "",

          vehicle_type:
            data.id_vehicle_type || "",

          model:
            data.model ?? "",

          variant:
            data.variant ?? "",

          color:
            data.id_color || "",

          customer:
            data.customer ?? "",

          sale_date:
            data.id_sale_date || "",

          insurance_company:
            data.insurance_company ?? "",

          policy_no:
            data.policy_no || "",

          policy_start_date:
            data.policy_start_date || "",

          policy_end_date:
            data.policy_end_date || "",

          last_service_km:
            data.last_service_km ?? "",

          last_service_type:
            data.last_service_type || "",

          last_service_date:
            data.last_service_date || "",

          primary_driver:
            data.primary_driver ?? "",

          assigned_drivers:
            Array.isArray(data.assigned_drivers)
              ? data.assigned_drivers.map(String)
              : [],

          rc_document: null,

          insurance_policy_document: null,
        });

        setExistingDocuments({
          vehicle_image: data.vehicle_image || "",
          rc_document:
            data.rc_document || "",

          insurance_policy_document:
            data.insurance_policy_document || "",
        });
      } catch (err) {
        console.error(
          "Vehicle load error:",
          err
        );

        setError(
          "Unable to load vehicle details."
        );
      } finally {
        setLoading(false);
      }
    };

    loadVehicle();
  }, [vehicleId]);

  // --------------------------------------------------
  // MODEL → VARIANT (DYNAMIC API)
  // --------------------------------------------------

  const filteredVariants = variants;

  const handleModelChange = async (event) => {
    const model = event.target.value;

    setForm((previous) => ({
      ...previous,
      model,
      variant: "",
    }));

    setFormErrors((previous) => ({
      ...previous,
      model: undefined,
      variant: undefined,
    }));

    setVariants([]);

    if (!model) {
      return;
    }

    try {
      const response = await fetch(
        `/ajax/load-variants/?model_id=${model}`,
        { credentials: "same-origin" }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setVariants(data || []);
    } catch (err) {
      console.error("Dynamic variant load error:", err);
      setError("Unable to load variants for the selected model.");
    }
  };

  // --------------------------------------------------
  // ADD MODEL
  // --------------------------------------------------

  const openModelModal = () => {
    setNewModelName("");
    setModalError("");
    setShowModelModal(true);
  };

  const closeModelModal = () => {
    if (!modalSaving) {
      setShowModelModal(false);
      setModalError("");
    }
  };

  const saveModel = async () => {
    const name = newModelName.trim();

    if (!name) {
      setModalError("Enter model name.");
      return;
    }

    setModalSaving(true);
    setModalError("");

    try {
      const response = await fetch("/ajax/add-model/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ name }),
      });

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        setModalError(data.message || "Unable to add model.");
        return;
      }

      const newModel = {
        id: data.id,
        name: data.name,
      };

      setModels((previous) => [...previous, newModel]);
      updateField("model", String(data.id));
      setVariants([]);

      setShowModelModal(false);
      setNewModelName("");
      setModalError("");
    } catch (err) {
      console.error("Add model error:", err);
      setModalError("Unable to add model.");
    } finally {
      setModalSaving(false);
    }
  };

  // --------------------------------------------------
  // ADD VARIANT
  // --------------------------------------------------

  const openVariantModal = () => {
    if (!form.model) {
      setError("Please select a model first.");
      return;
    }

    setNewVariantName("");
    setModalError("");
    setShowVariantModal(true);
  };

  const closeVariantModal = () => {
    if (!modalSaving) {
      setShowVariantModal(false);
      setModalError("");
    }
  };

  const saveVariant = async () => {
    const name = newVariantName.trim();

    if (!form.model) {
      setModalError("Select a model first.");
      return;
    }

    if (!name) {
      setModalError("Enter variant name.");
      return;
    }

    setModalSaving(true);
    setModalError("");

    try {
      const response = await fetch("/ajax/add-variant/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          model_id: form.model,
          name,
        }),
      });

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        setModalError(data.message || "Unable to add variant.");
        return;
      }

      const newVariant = {
        id: data.id,
        name: data.name,
        model_id: form.model,
      };

      setVariants((previous) => [...previous, newVariant]);
      updateField("variant", String(data.id));

      setShowVariantModal(false);
      setNewVariantName("");
      setModalError("");
    } catch (err) {
      console.error("Add variant error:", err);
      setModalError("Unable to add variant.");
    } finally {
      setModalSaving(false);
    }
  };

  // --------------------------------------------------
  // INPUT
  // --------------------------------------------------

  const updateField = (name, value) => {
    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    setFormErrors((previous) => ({
      ...previous,
      [name]: undefined,
    }));
  };


  const handleRegistrationChange = (value) => {
    const normalized = (value || "").toUpperCase().replace(/\s/g, "");
    updateField("registration_no", normalized);
    if (normalized && !VEHICLE_NUMBER_PATTERN.test(normalized)) setFormErrors((previous) => ({ ...previous, registration_no: [VEHICLE_NUMBER_ERROR] }));
  };

  const validateRegistration = async () => {
    const value = (form.registration_no || "").toUpperCase().replace(/\s/g, "");
    if (!value) return;
    if (!VEHICLE_NUMBER_PATTERN.test(value)) { setFormErrors((previous) => ({ ...previous, registration_no: [VEHICLE_NUMBER_ERROR] })); return; }
    if (isEditMode) return;
    const response = await fetch(`/ajax/check-registration/?registration_no=${encodeURIComponent(value)}`, { credentials: "same-origin" });
    if ((await response.json()).exists) setFormErrors((previous) => ({ ...previous, registration_no: ["Registration already exists"] }));
  };

  // --------------------------------------------------
  // DRIVER SELECTION
  // --------------------------------------------------

  const handleDriversChange = (event) => {
    const selected = Array.from(
      event.target.selectedOptions
    ).map((option) => option.value);

    if (selected.length > 5) {
      setFormErrors((previous) => ({
        ...previous,
        assigned_drivers: [
          "A vehicle can have a maximum of 5 drivers.",
        ],
      }));

      return;
    }

    updateField(
      "assigned_drivers",
      selected
    );
  };

  // --------------------------------------------------
  // CSRF
  // --------------------------------------------------

  const getCsrfToken = () => {
    const cookie = document.cookie
      .split("; ")
      .find(
        (row) =>
          row.startsWith("csrftoken=")
      );

    return cookie
      ? decodeURIComponent(
          cookie.split("=")[1]
        )
      : "";
  };

  // --------------------------------------------------
  // SUBMIT
  // --------------------------------------------------

  const handleSubmit = async (event) => {
    event.preventDefault();

    setSaving(true);
    setError("");
    setFormErrors({});

    try {
      const formData = new FormData();

      Object.entries(form).forEach(
        ([key, value]) => {
          if (key === "assigned_drivers") {
            value.forEach((driverId) => {
              formData.append(
                "assigned_drivers",
                driverId
              );
            });

            return;
          }

          if (
            value !== null &&
            value !== undefined &&
            value !== ""
          ) {
            formData.append(key, value);
          }
        }
      );

      const url = isEditMode
        ? `/ajax/vehicle/${vehicleId}/update/`
        : "/ajax/add-vehicle/";

      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
        body: formData,
      });

      const data = await response.json();

      if (
        !response.ok ||
        data.status !== "success"
      ) {
        setFormErrors(
          data.errors || {}
        );

        setError(
          data.message ||
            "Please correct the errors in the form."
        );

        return;
      }

      window.location.href =
        "/vehicle/";
    } catch (err) {
      console.error(
        "Vehicle save error:",
        err
      );

      setError(
        "Unable to save vehicle."
      );
    } finally {
      setSaving(false);
    }
  };

  // --------------------------------------------------
  // FIELD ERROR
  // --------------------------------------------------

  const fieldError = (name) => {
    const error = formErrors[name];

    if (!error) {
      return null;
    }

    return (
      <div className="new-vehicle-error">
        {Array.isArray(error)
          ? error.join(", ")
          : error}
      </div>
    );
  };

  // --------------------------------------------------
  // BACK
  // --------------------------------------------------

  const handleBack = () => {
    if (!saving) {
      window.location.href =
        "/vehicle/";
    }
  };

  // --------------------------------------------------
  // LOADING
  // --------------------------------------------------

  if (loading) {
    return (
      <div className="new-vehicle-page">
        <div className="new-vehicle-loading">
          {isEditMode
            ? "Loading vehicle details..."
            : "Loading vehicle form..."}
        </div>
      </div>
    );
  }

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  return (
    <div className="new-vehicle-page attached-style">

      {/* TOP HEADER */}
      <div className="new-vehicle-header attached-header">
        <div className="attached-header-left">
          <button
            type="button"
            className="attached-back-btn"
            onClick={handleBack}
            disabled={saving}
            title="Back"
          >
            ←
          </button>

          <div>
            <h2>
              {isEditMode ? "Edit Vehicle" : "New Vehicle"}
            </h2>
          </div>
        </div>

        <div className="attached-header-actions">
          <button
            type="button"
            className="attached-icon-btn"
            title="Add"
          >
            +
          </button>

          <button
            type="button"
            className="attached-icon-btn"
            title="Settings"
          >
            ⚙
          </button>

          <button
            type="submit"
            form="new-vehicle-form"
            className="attached-save-icon"
            disabled={saving}
            title={isEditMode ? "Update Vehicle" : "Save Vehicle"}
          >
            {saving ? "…" : "✓"}
          </button>
        </div>
      </div>

      {/* ERROR */}
      {error && (
        <div className="new-vehicle-alert">
          {error}
        </div>
      )}

      <form
        id="new-vehicle-form"
        className="new-vehicle-form attached-form"
        onSubmit={handleSubmit}
      >

        {/* MAIN VEHICLE FORM */}
        <section className="attached-form-section">

          <div className="attached-form-grid">

            {/* LEFT COLUMN */}

            

            <Field
              label="Registration No."
              value={form.registration_no}
              onChange={handleRegistrationChange}
              onBlur={validateRegistration}
              required
              error={fieldError("registration_no")}
            />
             <Field
              label="Vehicle Type"
              value={form.vehicle_type}
              onChange={(value) =>
                updateField("vehicle_type", value)
              }
              required
              error={fieldError("vehicle_type")}
              selectOptions={vehicleTypes}
              placeholder="Select Vehicle Type"
            />
            <div className="attached-dynamic-field">
              <Field
                label="Model"
                value={form.model}
                onChange={(value) =>
                  handleModelChange({ target: { value } })
                }
                error={fieldError("model")}
                selectOptions={models}
                placeholder="Select Model"
              />
              <button
                type="button"
                className="attached-add-remove-btn"
                onClick={openModelModal}
                disabled={saving}
              >
                Add/Remove
              </button>
            </div>

          <TomSelectField
  label="Customer"
  value={form.customer}
  onChange={(value) =>
    updateField(
      "customer",
      value
    )
  }
  options={customers}
  placeholder="Select Customer"
  error={fieldError(
    "customer"
  )}
/>

            <div className="attached-dynamic-field">
              <Field
                label="Variant"
                value={form.variant}
                onChange={(value) =>
                  updateField("variant", value)
                }
                error={fieldError("variant")}
                selectOptions={filteredVariants}
                placeholder={
                  form.model
                    ? "Select Variant"
                    : "Select Model First"
                }
                disabled={!form.model}
              />
              <button
                type="button"
                className="attached-add-remove-btn"
                onClick={openVariantModal}
                disabled={saving || !form.model}
              >
                Add/Remove
              </button>
            </div>

            <Field
              label="Sale Date"
              type="date"
              value={form.sale_date}
              onChange={(value) =>
                updateField("sale_date", value)
              }
              error={fieldError("sale_date")}
            />

            <Field
              label="Chassis No."
              value={form.chassis_no}
              onChange={(value) =>
                updateField("chassis_no", value)
              }
              error={fieldError("chassis_no")}
            />

            <ColorPaletteField
              label="Color"
              value={form.color}
              onChange={(value) =>
                updateField("color", value)
              }
              error={fieldError("color")}
            />

            <Field
              label="Engine No."
              value={form.engine_no}
              onChange={(value) =>
                updateField("engine_no", value)
              }
              error={fieldError("engine_no")}
            />

            <TomSelectField
  label="Insurance Company"
  value={form.insurance_company}
  onChange={(value) =>
    updateField("insurance_company", value)
  }
  options={insuranceCompanies}
  placeholder="Select Insurance Company"
  error={fieldError("insurance_company")}
/>
            <Field
              label="Policy No."
              value={form.policy_no}
              onChange={(value) =>
                updateField("policy_no", value)
              }
              error={fieldError("policy_no")}
            />

            <Field
              label="Policy Start Date"
              type="date"
              value={form.policy_start_date}
              onChange={(value) =>
                updateField("policy_start_date", value)
              }
              error={fieldError("policy_start_date")}
            />

            <Field
              label="Policy End Date"
              type="date"
              value={form.policy_end_date}
              onChange={(value) =>
                updateField("policy_end_date", value)
              }
              error={fieldError("policy_end_date")}
            />

            <Field
              label="Last Service KM"
              type="number"
              value={form.last_service_km}
              onChange={(value) =>
                updateField("last_service_km", value)
              }
              error={fieldError("last_service_km")}
            />

            <Field
              label="Last Service Type"
              value={form.last_service_type}
              onChange={(value) =>
                updateField("last_service_type", value)
              }
              error={fieldError("last_service_type")}
            />

            <Field
              label="Last Service Date"
              type="date"
              value={form.last_service_date}
              onChange={(value) =>
                updateField("last_service_date", value)
              }
              error={fieldError("last_service_date")}
            />

          </div>
        </section>

        {/* VEHICLE IMAGE & DOCUMENTS */}
        <section className="attached-secondary-section">
          <div className="attached-section-heading">
            <div>
              <h3>Vehicle Image &amp; Documents</h3>
              <p>Upload a clear vehicle photo and supporting documents.</p>
            </div>
          </div>

          <div className="attached-upload-grid">
            <FileField
              label="Vehicle Image"
              accept="image/*"
              existingFile={existingDocuments.vehicle_image}
              imagePreview
              onChange={(file) => updateField("vehicle_image", file)}
              error={fieldError("vehicle_image")}
            />
            <FileField
              label="RC Document"
              accept=".pdf,.jpg,.jpeg,.png"
              existingFile={existingDocuments.rc_document}
              onChange={(file) =>
                updateField("rc_document", file)
              }
              error={fieldError("rc_document")}
            />

            <FileField
              label="Insurance Policy Document"
              accept=".pdf,.jpg,.jpeg,.png"
              existingFile={
                existingDocuments.insurance_policy_document
              }
              onChange={(file) =>
                updateField(
                  "insurance_policy_document",
                  file
                )
              }
              error={fieldError("insurance_policy_document")}
            />
          </div>
        </section>

        {/* ASSIGNED DRIVERS */}
       {/* =====================================================
    DRIVER ASSIGNMENT
===================================================== */}

<DriverAssignmentSection
  vehicle={{
    id: vehicleId,
    registration_no: form.registration_no,
    model_name:
      models.find(
        (model) =>
          String(model.id) === String(form.model)
      )?.name || "",
    customer_name:
      customers.find(
        (customer) =>
          String(customer.id) === String(form.customer)
      )?.name || "",
  }}
  drivers={drivers}
  assignedDriverIds={form.assigned_drivers}
  onAssignDriver={(driverId) => {
    if (form.assigned_drivers.map(String).includes(String(driverId))) return;
    updateField("assigned_drivers", [...form.assigned_drivers, String(driverId)]);
  }}
  onUnassignDriver={(driverId) => {
    updateField(
      "assigned_drivers",
      form.assigned_drivers.filter((id) => String(id) !== String(driverId))
    );
  }}
  onOpenDriverMaster={() => { window.location.href = "/driver-master/"; }}
/>
        {/* BOTTOM ACTIONS */}
        <div className="new-vehicle-actions attached-bottom-actions">

          <button
            type="button"
            className="new-vehicle-cancel"
            onClick={handleBack}
            disabled={saving}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="new-vehicle-save attached-orange-submit"
            disabled={saving}
          >
            {saving
              ? "Saving..."
              : isEditMode
                ? "Update Vehicle"
                : "Save Vehicle"}
          </button>

        </div>

      </form>

      {/* MODEL MODAL */}
      {showModelModal && (
        <div className="attached-modal-backdrop" onMouseDown={closeModelModal}>
          <div
            className="attached-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="attached-modal-header">
              <h3>Add Model</h3>
              <button
                type="button"
                className="attached-modal-close"
                onClick={closeModelModal}
                disabled={modalSaving}
              >
                ×
              </button>
            </div>

            <div className="attached-modal-body">
              <label>Model Name</label>
              <input
                type="text"
                value={newModelName}
                onChange={(event) => setNewModelName(event.target.value)}
                placeholder="Enter Model Name"
                autoFocus
                onKeyDown={(event) => {
                  if (event.key === "Enter") saveModel();
                }}
              />
              {modalError && (
                <div className="attached-modal-error">{modalError}</div>
              )}

              <div className="attached-modal-list">
                {models.map((model) => (
                  <div className="attached-modal-list-row" key={model.id}>
                    <span>{model.name ?? model.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="attached-modal-footer">
              <button
                type="button"
                className="attached-modal-cancel"
                onClick={closeModelModal}
                disabled={modalSaving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="attached-modal-submit"
                onClick={saveModel}
                disabled={modalSaving}
              >
                {modalSaving ? "Saving..." : "Submit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VARIANT MODAL */}
      {showVariantModal && (
        <div className="attached-modal-backdrop" onMouseDown={closeVariantModal}>
          <div
            className="attached-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="attached-modal-header">
              <h3>Add Variant</h3>
              <button
                type="button"
                className="attached-modal-close"
                onClick={closeVariantModal}
                disabled={modalSaving}
              >
                ×
              </button>
            </div>

            <div className="attached-modal-body">
              <label>Model</label>
              <select
                value={form.model || ""}
                onChange={(event) => handleModelChange(event)}
                disabled={modalSaving}
              >
                <option value="">Select Model</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name ?? model.label}
                  </option>
                ))}
              </select>

              <label>Variant Name</label>
              <input
                type="text"
                value={newVariantName}
                onChange={(event) => setNewVariantName(event.target.value)}
                placeholder="Enter Variant Name"
                onKeyDown={(event) => {
                  if (event.key === "Enter") saveVariant();
                }}
              />

              {modalError && (
                <div className="attached-modal-error">{modalError}</div>
              )}

              <div className="attached-modal-list">
                {filteredVariants.map((variant) => (
                  <div className="attached-modal-list-row" key={variant.id}>
                    <span>{variant.name ?? variant.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="attached-modal-footer">
              <button
                type="button"
                className="attached-modal-cancel"
                onClick={closeVariantModal}
                disabled={modalSaving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="attached-modal-submit"
                onClick={saveVariant}
                disabled={modalSaving || !form.model}
              >
                {modalSaving ? "Saving..." : "Submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// --------------------------------------------------
// FIELD
// --------------------------------------------------

// --------------------------------------------------

function Field({
  label,
  type = "text",
  value,
  onChange,
  required = false,
  error,
  selectOptions = null,
  placeholder = "",
  disabled = false,
}) {
  return (
    <div className="attached-field">
      <label>
        {label}
        {required && <span className="required">*</span>}
      </label>

      {selectOptions ? (
        <select
          value={value || ""}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          className={
            error
              ? "new-vehicle-input input-error"
              : "new-vehicle-input"
          }
        >
          <option value="">
            {placeholder || `Select ${label}`}
          </option>

          {selectOptions.map((option) => (
            <option
              key={option.id ?? option.value}
              value={option.id ?? option.value}
            >
              {option.name ?? option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          type={type}
          value={value || ""}
          disabled={disabled}
          onChange={(event) =>
            onChange(event.target.value)
          }
          className={
            error
              ? "new-vehicle-input input-error"
              : "new-vehicle-input"
          }
        />
      )}

      {error}
    </div>
  );
}


// --------------------------------------------------
// SELECT
// --------------------------------------------------

function SelectField({
  label,
  value,
  onChange,
  options = [],
  placeholder,
  disabled = false,
  error,
}) {
  return (
    <div className="new-vehicle-field">

      <label>
        {label}
      </label>

      <select
        value={value || ""}
        disabled={disabled}
        onChange={(event) =>
          onChange(
            event.target.value
          )
        }
        className={
          error
            ? "new-vehicle-input input-error"
            : "new-vehicle-input"
        }
      >

        <option value="">
          {placeholder}
        </option>

        {options.map((option) => (
          <option
            key={
              option.id ??
              option.value
            }
            value={
              option.id ??
              option.value
            }
          >
            {option.name ??
              option.label}
          </option>
        ))}

      </select>

      {error}

    </div>
  );
}
function TomSelectField({
  label,
  value,
  onChange,
  options = [],
  placeholder,
  error,
}) {
  const selectRef = useRef(null);
  const tomSelectRef = useRef(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!selectRef.current) return;

    if (!window.TomSelect) {
      console.error("Tom Select is not loaded.");
      return;
    }

    const selectElement = selectRef.current;

    if (tomSelectRef.current) {
      tomSelectRef.current.destroy();
      tomSelectRef.current = null;
    }

    selectElement.innerHTML = "";

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder || "Select";
    selectElement.appendChild(placeholderOption);

    options.forEach((option) => {
      const optionElement = document.createElement("option");

      optionElement.value =
        option.id ?? option.value;

      optionElement.textContent =
        option.name ?? option.label;

      selectElement.appendChild(optionElement);
    });

    const tomSelect = new window.TomSelect(
      selectElement,
      {
        create: false,
        allowEmptyOption: true,
        maxOptions: 500,
        searchField: ["text"],
        sortField: {
          field: "text",
          direction: "asc",
        },

        onChange(selectedValue) {
          onChangeRef.current(selectedValue);
        },
      }
    );

    tomSelectRef.current = tomSelect;

    return () => {
      if (tomSelectRef.current) {
        tomSelectRef.current.destroy();
        tomSelectRef.current = null;
      }
    };
  }, [options, placeholder]);

  useEffect(() => {
    if (!tomSelectRef.current) return;

    const selectedValue =
      value === null || value === undefined
        ? ""
        : String(value);

    if (
      tomSelectRef.current.getValue() !==
      selectedValue
    ) {
      tomSelectRef.current.setValue(
        selectedValue,
        true
      );
    }
  }, [value]);

  return (
    <div className="new-vehicle-field tom-select-field">
      <label>{label}</label>

      <select
        ref={selectRef}
        className={
          error
            ? "new-vehicle-input input-error"
            : "new-vehicle-input"
        }
      />

      {error}
    </div>
  );
}

// --------------------// --------------------------------------------------
// TOM SELECT
// --------------------------------------------------

function TomSelectMultiField({
  label,
  value = [],
  onChange,
  options = [],
  placeholder,
  error,
  maxItems = 5,
}) {
  const selectRef = useRef(null);
  const tomSelectRef = useRef(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!selectRef.current) return;

    if (!window.TomSelect) {
      console.error("Tom Select is not loaded.");
      return;
    }

    const selectElement = selectRef.current;

    if (tomSelectRef.current) {
      tomSelectRef.current.destroy();
      tomSelectRef.current = null;
    }

    selectElement.innerHTML = "";

    options.forEach((option) => {
      const optionElement = document.createElement("option");

      optionElement.value =
        option.id ?? option.value;

      optionElement.textContent =
        option.name ?? option.label;

      selectElement.appendChild(optionElement);
    });

    const tomSelect = new window.TomSelect(
      selectElement,
      {
        plugins: ["remove_button"],
        maxItems,
        create: false,
        searchField: ["text"],
        sortField: {
          field: "text",
          direction: "asc",
        },
        placeholder: placeholder || "Select",

        onChange(selectedValues) {
          const selected = Array.isArray(selectedValues)
            ? selectedValues
            : selectedValues
              ? [selectedValues]
              : [];

          onChangeRef.current(
            selected.map(String)
          );
        },
      }
    );

    tomSelectRef.current = tomSelect;

    return () => {
      if (tomSelectRef.current) {
        tomSelectRef.current.destroy();
        tomSelectRef.current = null;
      }
    };
  }, [options, placeholder, maxItems]);

  useEffect(() => {
    if (!tomSelectRef.current) return;

    const selectedValues = Array.isArray(value)
      ? value.map(String)
      : [];

    tomSelectRef.current.setValue(
      selectedValues,
      true
    );
  }, [value]);

  return (
    <div className="new-vehicle-field">
      <label>{label}</label>

      <select
        ref={selectRef}
        multiple
        className={
          error
            ? "new-vehicle-input input-error"
            : "new-vehicle-input"
        }
      />

      {error}
    </div>
  );
}
const VEHICLE_COLORS = [
  ["Black", "#000000"], ["Red", "#ff0000"], ["Dravit Grey", "#62666b"],
  ["Blue", "#0000ff"], ["Grey", "#2468c8"], ["Brown", "#a40808"],
  ["Green", "#008000"], ["Dark Pink", "#ff0060"], ["Purple", "#a000b5"],
  ["Yellow", "#ffc000"],
];

function ColorPaletteField({ label, value, onChange, error }) {
  const [open, setOpen] = useState(false);
  const selected = VEHICLE_COLORS.find(([name]) => name === value);
  return (
    <div className="new-vehicle-field color-palette-field">
      <label>{label}</label>
      <div className={`color-picker ${error ? "input-error" : ""}`}>
        <button type="button" className="color-picker-trigger" onClick={() => setOpen((current) => !current)}>
          {selected ? <i style={{ background: selected[1] }} /> : <i className="empty-color-swatch" />}
          <span>{selected?.[0] || "Select Color"}</span>
          <b>⌄</b>
        </button>
        {open && (
          <div className="color-picker-menu">
            <button type="button" className="color-picker-option color-picker-placeholder" onClick={() => { onChange(""); setOpen(false); }}>
              Select Color
            </button>
            {VEHICLE_COLORS.map(([name, color]) => (
              <button type="button" key={name} className={`color-picker-option ${name === value ? "selected" : ""}`} onClick={() => { onChange(name); setOpen(false); }}>
                <i style={{ background: color }} />
                <span>{name}</span>
                {name === value && <b>✓</b>}
              </button>
            ))}
          </div>
        )}
      </div>
      {selected && <span className="selected-color-label"><i style={{ background: selected[1] }} />{selected[0]}</span>}
      {error}
    </div>
  );
}

// FILE
// --------------------------------------------------

function FileField({
  label,
  onChange,
  existingFile,
  error,
  accept,
  imagePreview = false,
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageHovered, setImageHovered] = useState(false);
  const inputId = `upload-${label.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;
  const previewUrl = selectedFile && imagePreview
    ? URL.createObjectURL(selectedFile)
    : imagePreview && typeof existingFile === "string" ? existingFile : "";

  const handleChange = (event) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    onChange(file);
  };

  return (
    <div className={`new-vehicle-field upload-card ${imagePreview ? "upload-card-image" : ""}`}>
      <div className="upload-card-title">
        <span className="upload-card-icon">{imagePreview ? "▧" : "↥"}</span>
        <label>{label}</label>
      </div>

      <input
        type="file"
        id={inputId}
        accept={accept}
        hidden
        className={
          error
            ? "new-vehicle-input input-error"
            : "new-vehicle-input"
        }
        onChange={handleChange}
      />

      <label className="upload-dropzone" htmlFor={inputId}>
        <span className="upload-dropzone-icon">{imagePreview ? "▧" : "＋"}</span>
        <strong>{selectedFile ? selectedFile.name : "Choose a file"}</strong>
        <span>{imagePreview ? "JPG, PNG up to 5 MB" : "PDF, JPG or PNG"}</span>
      </label>

      {imagePreview && previewUrl && (
        <div
          className="uploaded-image-preview"
          onMouseEnter={() => setImageHovered(true)}
          onMouseLeave={() => setImageHovered(false)}
        >
          <img src={previewUrl} alt="Uploaded vehicle" />
          <span>{selectedFile ? "New image selected" : "Already uploaded"}</span>
          {imageHovered && (
            <div className="vehicle-image-modal" role="dialog" aria-label="Vehicle image preview">
              <img src={previewUrl} alt="Large vehicle preview" />
              <span>Move the pointer away to close</span>
            </div>
          )}
        </div>
      )}

      {existingFile && (
        <small className="upload-existing">
          {!imagePreview && <>Existing document:&nbsp;</>}

          {!imagePreview && typeof existingFile === "string" && (
            <a href={existingFile} target="_blank" rel="noreferrer">View document</a>
          )}
        </small>
      )}

      {error}

    </div>
  );
}

export default NewVehicle;
