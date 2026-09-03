import { useEffect, useMemo, useState } from "react";
import "./NewVehicle.css";

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
  rc_document: null,
  insurance_policy_document: null,
};

function NewVehicle() {
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

  // -----------------------------------------
  // LOAD FORM OPTIONS
  // -----------------------------------------

  useEffect(() => {
    const loadOptions = async () => {
      try {
        setLoading(true);

        const response = await fetch("/ajax/vehicle-form-data/", {
          credentials: "same-origin",
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        setCustomers(data.customers || []);
        setModels(data.models || []);
        setVariants(data.variants || []);
        setInsuranceCompanies(
  (data.insurance_companies || []).map((company) => ({
    value: company.id,
    label: company.ins_co_name,
  }))
);
        setDrivers(data.drivers || []);
        setVehicleTypes(data.vehicle_types || []);
      } catch (err) {
        console.error("Vehicle form data error:", err);
        setError("Unable to load vehicle form data.");
      } finally {
        setLoading(false);
      }
    };

    loadOptions();
  }, []);

  // -----------------------------------------
  // MODEL → VARIANT
  // -----------------------------------------

  const filteredVariants = useMemo(() => {
    if (!form.model) {
      return [];
    }

    return variants.filter(
      (variant) =>
        String(variant.model_id) === String(form.model)
    );
  }, [form.model, variants]);

  // -----------------------------------------
  // INPUT
  // -----------------------------------------

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

  const handleModelChange = (event) => {
    const model = event.target.value;

    setForm((previous) => ({
      ...previous,
      model,
      variant: "",
    }));
  };

  const handleDriversChange = (event) => {
    const selected = Array.from(
      event.target.selectedOptions
    ).map((option) => option.value);

    if (selected.length > 5) {
      return;
    }

    updateField("assigned_drivers", selected);
  };

  // -----------------------------------------
  // CSRF
  // -----------------------------------------

  const getCsrfToken = () => {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="));

    return cookie
      ? decodeURIComponent(cookie.split("=")[1])
      : "";
  };

  // -----------------------------------------
  // SUBMIT
  // -----------------------------------------

  const handleSubmit = async (event) => {
    event.preventDefault();

    setSaving(true);
    setError("");
    setFormErrors({});

    try {
      const formData = new FormData();

      Object.entries(form).forEach(([key, value]) => {
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
      });

      const response = await fetch(
        "/ajax/add-vehicle/",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": getCsrfToken(),
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (
        !response.ok ||
        data.status !== "success"
      ) {
        setFormErrors(data.errors || {});
        setError(
          data.message ||
            "Please correct the errors in the form."
        );
        return;
      }

      window.location.href = "/vehicle/";
    } catch (err) {
      console.error("Vehicle save error:", err);
      setError("Unable to save vehicle.");
    } finally {
      setSaving(false);
    }
  };

  // -----------------------------------------
  // FIELD ERROR
  // -----------------------------------------

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

  // -----------------------------------------
  // BACK
  // -----------------------------------------

  const handleBack = () => {
    if (!saving) {
      window.location.href = "/vehicle/";
    }
  };

  if (loading) {
    return (
      <div className="new-vehicle-page">
        <div className="new-vehicle-loading">
          Loading vehicle form...
        </div>
      </div>
    );
  }

  return (
    <div className="new-vehicle-page">

      {/* HEADER */}

      <div className="new-vehicle-header">
        <div>
          <h2>New Vehicle Master</h2>
          <p>
            Register a new vehicle
          </p>
        </div>

        <button
          type="button"
          className="new-vehicle-back"
          onClick={handleBack}
          disabled={saving}
        >
          ← Back to Vehicle Master
        </button>
      </div>

      {error && (
        <div className="new-vehicle-alert">
          {error}
        </div>
      )}

      <form
        className="new-vehicle-form"
        onSubmit={handleSubmit}
      >

        {/* VEHICLE DETAILS */}

        <section className="new-vehicle-section">

          <div className="new-vehicle-section-title">
            Vehicle Details
          </div>

          <div className="new-vehicle-grid">

            <Field
              label="Registration No."
              name="registration_no"
              value={form.registration_no}
              onChange={(value) =>
                updateField(
                  "registration_no",
                  value.toUpperCase()
                )
              }
              required
              error={fieldError("registration_no")}
            />

            <Field
              label="Chassis No."
              name="chassis_no"
              value={form.chassis_no}
              onChange={(value) =>
                updateField("chassis_no", value)
              }
              error={fieldError("chassis_no")}
            />

            <Field
              label="Engine No."
              name="engine_no"
              value={form.engine_no}
              onChange={(value) =>
                updateField("engine_no", value)
              }
              error={fieldError("engine_no")}
            />

            <SelectField
              label="Vehicle Type"
              value={form.vehicle_type}
              onChange={(value) =>
                updateField("vehicle_type", value)
              }
              options={vehicleTypes}
              placeholder="Select Vehicle Type"
              error={fieldError("vehicle_type")}
            />

            <SelectField
              label="Model"
              value={form.model}
              onChange={(value) => {
                handleModelChange({
                  target: {
                    value,
                  },
                });
              }}
              options={models}
              placeholder="Select Model"
              error={fieldError("model")}
            />

            <SelectField
              label="Variant"
              value={form.variant}
              onChange={(value) =>
                updateField("variant", value)
              }
              options={filteredVariants}
              placeholder={
                form.model
                  ? "Select Variant"
                  : "Select Model First"
              }
              disabled={!form.model}
              error={fieldError("variant")}
            />

            <Field
              label="Color"
              name="color"
              value={form.color}
              onChange={(value) =>
                updateField("color", value)
              }
              error={fieldError("color")}
            />

            <SelectField
              label="Customer"
              value={form.customer}
              onChange={(value) =>
                updateField("customer", value)
              }
              options={customers}
              placeholder="Select Customer"
              error={fieldError("customer")}
            />

            <Field
              label="Sale Date"
              type="date"
              value={form.sale_date}
              onChange={(value) =>
                updateField("sale_date", value)
              }
              error={fieldError("sale_date")}
            />

          </div>

        </section>

        {/* INSURANCE */}

        <section className="new-vehicle-section">

          <div className="new-vehicle-section-title">
            Insurance Details
          </div>

          <div className="new-vehicle-grid">

            <SelectField
              label="Insurance Company"
              value={form.insurance_company}
              onChange={(value) =>
                updateField(
                  "insurance_company",
                  value
                )
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
                updateField(
                  "policy_start_date",
                  value
                )
              }
              error={fieldError(
                "policy_start_date"
              )}
            />

            <Field
              label="Policy End Date"
              type="date"
              value={form.policy_end_date}
              onChange={(value) =>
                updateField(
                  "policy_end_date",
                  value
                )
              }
              error={fieldError(
                "policy_end_date"
              )}
            />

          </div>

        </section>

        {/* SERVICE */}

        <section className="new-vehicle-section">

          <div className="new-vehicle-section-title">
            Last Service
          </div>

          <div className="new-vehicle-grid">

            <Field
              label="Last Service KM"
              type="number"
              value={form.last_service_km}
              onChange={(value) =>
                updateField(
                  "last_service_km",
                  value
                )
              }
              error={fieldError(
                "last_service_km"
              )}
            />

            <Field
              label="Last Service Type"
              value={form.last_service_type}
              onChange={(value) =>
                updateField(
                  "last_service_type",
                  value
                )
              }
              error={fieldError(
                "last_service_type"
              )}
            />

            <Field
              label="Last Service Date"
              type="date"
              value={form.last_service_date}
              onChange={(value) =>
                updateField(
                  "last_service_date",
                  value
                )
              }
              error={fieldError(
                "last_service_date"
              )}
            />

          </div>

        </section>

        {/* DOCUMENTS */}

        <section className="new-vehicle-section">

          <div className="new-vehicle-section-title">
            Documents
          </div>

          <div className="new-vehicle-grid">

            <FileField
              label="RC Document"
              onChange={(file) =>
                updateField(
                  "rc_document",
                  file
                )
              }
              error={fieldError(
                "rc_document"
              )}
            />

            <FileField
              label="Insurance Policy Document"
              onChange={(file) =>
                updateField(
                  "insurance_policy_document",
                  file
                )
              }
              error={fieldError(
                "insurance_policy_document"
              )}
            />

          </div>

        </section>

        {/* DRIVERS */}

<section className="new-vehicle-section">

  <div className="new-vehicle-section-title">
    <span>Driver Assignment</span>

    <button
      type="button"
      className="assign-driver-btn"
      onClick={() => {
        window.location.href = "/driver-master/";
      }}
    >
      Assign Driver
    </button>
  </div>

  {/* driver table / assignment UI */}

</section>



        {/* ACTIONS */}

        <div className="new-vehicle-actions">

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
            className="new-vehicle-save"
            disabled={saving}
          >
            {saving
              ? "Saving..."
              : "Save Vehicle"}
          </button>

        </div>

      </form>
    </div>
  );
}


// -----------------------------------------
// FIELD COMPONENT
// -----------------------------------------

function Field({
  label,
  type = "text",
  value,
  onChange,
  required = false,
  error,
}) {
  return (
    <div className="new-vehicle-field">

      <label>
        {label}

        {required && (
          <span className="required">*</span>
        )}
      </label>

      <input
        type={type}
        value={value || ""}
        onChange={(event) =>
          onChange(event.target.value)
        }
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


// -----------------------------------------
// SELECT
// -----------------------------------------

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

      <label>{label}</label>

      <select
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
      >

        <option value="">
          {placeholder}
        </option>

        {options.map((option) => (
          <option
            key={option.id ?? option.value}
            value={option.id ?? option.value}
          >
            {option.name ?? option.label}
          </option>
        ))}

      </select>

      {error}

    </div>
  );
}


// -----------------------------------------
// FILE
// -----------------------------------------

function FileField({
  label,
  onChange,
  error,
}) {
  return (
    <div className="new-vehicle-field">

      <label>{label}</label>

      <input
        type="file"
        className={
          error
            ? "new-vehicle-input input-error"
            : "new-vehicle-input"
        }
        onChange={(event) =>
          onChange(event.target.files?.[0] || null)
        }
      />

      {error}

    </div>
  );
}

export default NewVehicle;