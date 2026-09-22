import React, { useMemo, useRef, useState } from "react";
import "./JobCardEntry.css";
import RepairProgress from "../RepairProgress/RepairProgress";
const TABS = [
  ["overview", "Overview"],
  ["job", "Job Details"],
  ["estimate", "Estimate"],
  ["inspection", "Inspection"],
  ["parts", "Parts"],
  ["labour", "Labour"],
  ["claim", "Claim"],
  ["approval", "Approval"],
  ["repair", "Repair Progress"],
  ["quality", "Quality Check"],
  ["delivery", "Delivery"],
];

const ESTIMATE_PANELS = [
  ["front_bumper", "Front Bumper"], ["bonnet", "Bonnet"], ["windshield", "Windshield"],
  ["roof", "Roof"], ["dicky", "Dicky"], ["rear_bumper", "Rear Bumper"],
  ["front_right_fender", "Fender RH"], ["front_left_fender", "Fender LH"],
  ["right_front_door", "Door RH F"], ["left_front_door", "Door LH F"],
  ["right_rear_door", "Door RH R"], ["left_rear_door", "Door LH R"],
  ["right_quarter", "Quarter RH"], ["left_quarter", "Quarter LH"],
  ["headlamp_right", "Headlamp RH"], ["headlamp_left", "Headlamp LH"],
  ["tail_lamp_right", "Tail Lamp RH"], ["tail_lamp_left", "Tail Lamp LH"],
];

const ESTIMATE_ACTIONS = [
  ["replace", "Replace / New", "REPL", "Replace", 1],
  ["repair", "Repair", "REP", "Repair", 2],
  ["paint", "Paint", "PNT", "Paint", 2],
  ["rr", "Remove & Refit", "RR", "Remove & Refit", 1],
  ["dent", "Dent", "DENT", "Dent Repair", 1.5],
  ["align", "Alignment / Fitting", "FIT", "Alignment / Fitting", 1],
];

const money = (value) =>
  `₹ ${Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const emptyPart = () => ({
  id: "",
  part_no: "",
  description: "",
  qty: 1,
  rate: 0,
  amount: 0,
});

const emptyLabour = () => ({
  id: "",
  job_code: "",
  description: "",
  hrs: 1,
  rate: 0,
  amount: 0,
  paint_panel_type: "",
});

function csrf() {
  const match = document.cookie
    .split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith("csrftoken="));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

function calculateRows(rows, qtyKey, rateKey) {
  return rows.map((row) => ({
    ...row,
    amount: Number(row[qtyKey] || 0) * Number(row[rateKey] || 0),
  }));
}

function Field({ label, children, hint }) {
  return (
    <label className="jc-field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

function ReadOnly({ label, value }) {
  return (
    <div className="jc-readonly">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}

function Empty({ title, text }) {
  return (
    <div className="jc-empty">
      <div className="jc-empty-icon">+</div>
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

export default function JobCardEntry({ payload = window.__JOBCARD_ENTRY__ || {} }) {
  console.log("JobCardEntry payload:", payload.vehicle);
  const job = payload.job || {};
  const claim = payload.claim || null;
  const vehicle = payload.vehicle || {};
 const customer = payload?.customer || {
  name:
    payload?.customer_name ||
    job?.customer_name ||
    "",
  mobile:
    payload?.customer_mobile ||
    job?.customer_mobile ||
    "",
};

const advisor = payload?.advisor || {
  name:
    payload?.advisor_name ||
    job?.advisor_name ||
    "",
};
  const locked = Boolean(payload.isJobcardLocked);
  const canEdit = payload.canEditJobcardEntries !== false && !locked;

  const [tab, setTab] = useState("overview");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const inspection = payload.inventory || {};
  const rotationPhotos = payload.rotationPhotos || payload.rotation_photos || [];
  const vehiclePhotoSlots = payload.vehiclePhotoSlots || payload.vehicle_photo_slots || [];

  const [form, setForm] = useState({
    job_created_date: payload.jobCreatedDate || "",
    vehicle_inward_by: payload.vehicleInwardBy || "",
    insurance_company: payload.insuranceCompany || "",
    policy_no: payload.policyNo || "",
    jobcard_main_status: job.repair_status || "Open",
    road_test_done: Boolean(payload.roadTestDone),
    washing_done: Boolean(payload.washingDone),
    ready_for_delivery: Boolean(payload.readyForDelivery),
    direct_vehicle: payload.directVehicleId || "",
    gate_entry_id: payload.gateEntryId || "",
    fuel_percent: payload.fuelPercent ?? inspection.fuel_percent ?? 0,
    cng_percent: payload.cngPercent ?? inspection.cng_percent ?? 0,
    mud_flap_count: payload.mudFlapCount ?? inspection.mud_flap_count ?? 0,
    floor_mat_count: payload.floorMatCount ?? inspection.floor_mat_count ?? 0,
    lh_mirror: Boolean(payload.lhMirror ?? inspection.lh_mirror),
    rh_mirror: Boolean(payload.rhMirror ?? inspection.rh_mirror),
    center_mirror: Boolean(payload.centerMirror ?? inspection.center_mirror),
    jack: Boolean(payload.jack ?? inspection.jack),
    tool_kit: Boolean(payload.toolKit ?? inspection.tool_kit),
    frt_wiper: Boolean(payload.frtWiper ?? inspection.frt_wiper),
    rr_wiper: Boolean(payload.rrWiper ?? inspection.rr_wiper),
    accessories: Boolean(payload.accessories ?? inspection.accessories),
    stereo: Boolean(payload.stereo ?? inspection.stereo),
    battery: Boolean(payload.battery ?? inspection.battery),
    number_plate: Boolean(payload.numberPlate ?? inspection.number_plate),
    inventory_remarks: payload.inventoryRemarks ?? inspection.remarks ?? "",
    repair_instructions: payload.repairInstructions || [""],
    damage_marks: payload.damageMarks || [],
  });

  const [parts, setParts] = useState(
    (payload.parts || []).length ? payload.parts : [emptyPart()]
  );
  const [labours, setLabours] = useState(
    (payload.labours || []).length ? payload.labours : [emptyLabour()]
  );
  const [tyres, setTyres] = useState(
    payload.tyres || inspection.tyres || []
  );
  const [show360, setShow360] = useState(false);
  const [rotationIndex, setRotationIndex] = useState(0);
  const rotationDrag = useRef({ startX: null, accumulated: 0 });
  const [estimatePanel, setEstimatePanel] = useState("");
  const [estimateAction, setEstimateAction] = useState("replace");
  const [builderPart, setBuilderPart] = useState({ part_no: "", description: "", qty: 1, rate: 0 });
  const [builderLabour, setBuilderLabour] = useState({ job_code: "REPL", description: "", hrs: 1, rate: 0, paint_panel_type: "" });
  const [builderBusy, setBuilderBusy] = useState(false);
  const [requisitionBusy, setRequisitionBusy] = useState(false);
  const [estimatePhotoIndex, setEstimatePhotoIndex] = useState(0);

  // Phase 3: Approval / AI review / customer consent
  const [approvalBusy, setApprovalBusy] = useState(false);
  const [approvalNotice, setApprovalNotice] = useState("");
  const [approvalError, setApprovalError] = useState("");
  const [aiRows, setAiRows] = useState(payload.damageAiSuggestions || []);
  const [approvalPartRows, setApprovalPartRows] = useState(payload.approvalParts || []);
  const [approvalLabourRows, setApprovalLabourRows] = useState(payload.approvalLabours || []);
  const [evidenceType, setEvidenceType] = useState("WhatsApp");
  const [evidenceCaption, setEvidenceCaption] = useState("");
  const [evidenceFile, setEvidenceFile] = useState(null);


  const partsTotal = useMemo(
    () => parts.reduce((sum, row) => sum + Number(row.qty || 0) * Number(row.rate || 0), 0),
    [parts]
  );
  const labourTotal = useMemo(
    () => labours.reduce((sum, row) => sum + Number(row.hrs || 0) * Number(row.rate || 0), 0),
    [labours]
  );
  const grandTotal = partsTotal + labourTotal;

  const update = (key, value) => setForm((p) => ({ ...p, [key]: value }));

  const updatePart = (index, key, value) => {
    setParts((rows) =>
      rows.map((row, i) => {
        if (i !== index) return row;
        const next = { ...row, [key]: value };
        next.amount = Number(next.qty || 0) * Number(next.rate || 0);
        return next;
      })
    );
  };

  const updateLabour = (index, key, value) => {
    setLabours((rows) =>
      rows.map((row, i) => {
        if (i !== index) return row;
        const next = { ...row, [key]: value };
        next.amount = Number(next.hrs || 0) * Number(next.rate || 0);
        return next;
      })
    );
  };

  async function lookupPart(index) {
    const partNo = String(parts[index].part_no || "").trim().toUpperCase();
    if (!partNo) return;
    try {
      const response = await fetch(
        `/ajax/part-lookup/?item_code=${encodeURIComponent(partNo)}&t=${Date.now()}`,
        { credentials: "same-origin" }
      );
      const data = await response.json();
      if (data.status !== "success") {
        setError(data.message || "Part not found.");
        return;
      }
      setParts((rows) =>
        rows.map((row, i) =>
          i === index
            ? {
                ...row,
                part_no: partNo,
                description: data.description || "",
                rate: data.rate || 0,
                qty: row.qty || 1,
                amount: Number(row.qty || 1) * Number(data.rate || 0),
              }
            : row
        )
      );
      setError("");
    } catch {
      setError("Unable to lookup part.");
    }
  }

  const rotate360 = (distance) => {
    if (rotationPhotos.length < 2) return;
    rotationDrag.current.accumulated += distance;
    while (Math.abs(rotationDrag.current.accumulated) >= 24) {
      const direction = rotationDrag.current.accumulated < 0 ? 1 : -1;
      setRotationIndex((current) => (current + direction + rotationPhotos.length) % rotationPhotos.length);
      rotationDrag.current.accumulated += rotationDrag.current.accumulated < 0 ? 24 : -24;
    }
  };

  const handle360PointerDown = (event) => {
    if (rotationPhotos.length < 2) return;
    rotationDrag.current.startX = event.clientX;
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const handle360PointerMove = (event) => {
    if (rotationDrag.current.startX === null) return;
    rotate360(event.clientX - rotationDrag.current.startX);
    rotationDrag.current.startX = event.clientX;
  };

  const handle360PointerUp = () => {
    rotationDrag.current.startX = null;
  };

  function appendToFormData(fd) {
    Object.entries(form).forEach(([key, value]) => {
      if (Array.isArray(value)) return;
      if (typeof value === "boolean") {
        if (value) fd.append(key, "on");
        return;
      }
      fd.append(key, value ?? "");
    });

    fd.delete("repair_instructions");
    form.repair_instructions.forEach((value) => fd.append("repair_instruction[]", value));

    fd.delete("damage_marks");
    fd.append("damage_marks", JSON.stringify(form.damage_marks || []));

    parts.forEach((row) => {
      fd.append("part_id[]", row.id || "");
      fd.append("part_no[]", row.part_no || "");
      fd.append("part_desc[]", row.description || "");
      fd.append("qty[]", row.qty ?? 0);
      fd.append("rate[]", row.rate ?? 0);
      fd.append("amount[]", row.amount ?? 0);
    });

    labours.forEach((row) => {
      fd.append("labour_id[]", row.id || "");
      fd.append("job_code[]", row.job_code || "");
      fd.append("lab_desc[]", row.description || "");
      fd.append("hrs[]", row.hrs ?? 0);
      fd.append("lab_rate[]", row.rate ?? 0);
      fd.append("lab_amount[]", row.amount ?? 0);
      fd.append("labour_paint_panel_type[]", row.paint_panel_type || "");
    });

    tyres.forEach((row) => {
      fd.append("tyre_position[]", row.position || "");
      fd.append("tyre_make[]", row.make || "");
      fd.append("tyre_size[]", row.size || "");
      fd.append("tyre_depth[]", row.depth || "");
      fd.append("tyre_wheel_cap[]", row.wheel_cap || "");
    });

    // Legacy Django expects the vehicle-condition photo input names directly
    // in request.FILES, e.g. vehicle_condition_photo_1, vehicle_condition_photo_2.
    vehiclePhotoSlots.forEach((slot) => {
      if (!slot.inputName && !slot.input_name) return;
      const inputName = slot.inputName || slot.input_name;
      const input = document.querySelector(`[data-vehicle-photo-input="${inputName}"]`);
      Array.from(input?.files || []).forEach((file) => fd.append(inputName, file));
    });
  }

  async function saveJobCard(event) {
    event?.preventDefault();
    if (!canEdit) return;

    if (form.jobcard_main_status === "Closed" && String(job.repair_status || "") !== "Closed") {
      const readiness = payload.closeReadyStatus || {};
      const missing = [];
      if (!(readiness.work_completed ?? payload.repairCompleted)) missing.push("Work Completed");
      if (!(readiness.qc_done ?? payload.qualityCompleted)) missing.push("Quality Check");
      if (!(readiness.ri_done ?? payload.reinspectionDone)) missing.push("Re-inspection");
      if (!readiness.part_entry_complete) missing.push("Part Entry");
      if (!form.road_test_done) missing.push("Road Test");
      if (!form.washing_done) missing.push("Washing");
      if (!form.ready_for_delivery) missing.push("Ready for Delivery");
      if (missing.length) {
        setError(`Before closing Job Card, complete: ${missing.join(", ")}`);
        setTab("delivery");
        return;
      }
      if (!window.confirm("After closing the Job Card, normal users cannot re-open it. Only Admin or Manager can re-open. Do you want to close this Job Card?")) return;
    }

    setSaving(true);
    setMessage("");
    setError("");

    const fd = new FormData();
    appendToFormData(fd);

    try {
      const response = await fetch(payload.submitUrl || window.location.href, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
        body: fd,
      });
      const data = await response.json().catch(() => null);

      if (!response.ok || (data && data.status === "error")) {
        throw new Error(
          data?.message ||
            (data?.errors ? JSON.stringify(data.errors) : "Unable to save Job Card.")
        );
      }

      setMessage("Job Card saved successfully.");
      if (data?.redirect_url) {
        window.location.href = data.redirect_url;
      } else if (data?.id && !payload.jobId) {
        window.location.href = `/jobCard/${data.id}/edit/?saved=1`;
      }
    } catch (err) {
      setError(err.message || "Unable to save Job Card.");
    } finally {
      setSaving(false);
    }
  }

  function addPart() {
    if (!canEdit) return;
    setParts((rows) => [...rows, emptyPart()]);
    setTab("parts");
  }

  function addLabour() {
    if (!canEdit) return;
    setLabours((rows) => [...rows, emptyLabour()]);
    setTab("labour");
  }
  function renderRepairProgress() {
    return (
      <RepairProgress jobProgress={payload.jobProgress} jobRepairStatus={payload.jobRepairStatus} /> )
  } 
  function renderOverview() {
    return (
      <>
           <div className="jc-overview-grid">
          <section className="jc-card">
            <header><div><span className="jc-kicker">WORK ORDER</span><h3>Job Card Details</h3></div></header>
            <div className="jc-info-list">
              <ReadOnly label="Job Date" value={job.job_date_display} />
              <ReadOnly label="Gate In" value={job.gate_in_display} />
              <ReadOnly label="Inward Type" value={job.vehicle_inward_type} />
              <ReadOnly label="Inward By" value={job.vehicle_inward_by || form.vehicle_inward_by} />
              <ReadOnly label="Status" value={form.jobcard_main_status} />
            </div>
          </section>

          <section className="jc-card">
            <header><div><span className="jc-kicker">VEHICLE</span><h3>{vehicle.registration_no || "Vehicle"}</h3></div></header>
            <div className="jc-info-list">
              <ReadOnly label="Model / Variant" value={vehicle.model_variant} />
              <ReadOnly label="Chassis" value={vehicle.chassis_no} />
              <ReadOnly label="Engine" value={vehicle.engine_no} />
              <ReadOnly label="Colour" value={vehicle.color} />
              <ReadOnly label="KM" value={job.km} />
            </div>
          </section>

          <section className="jc-card">
            <header><div><span className="jc-kicker">CUSTOMER</span><h3>{customer.name || "Customer"}</h3></div></header>
            <div className="jc-info-list">
              <ReadOnly label="Type" value={customer.customer_type} />
              <ReadOnly label="Mobile" value={customer.mobile_no} />
              <ReadOnly label="Email" value={customer.email} />
              <ReadOnly label="City" value={customer.city} />
            </div>
          </section>
        </div>

        <section className="jc-card jc-cost-card">
          <header><div><span className="jc-kicker">ESTIMATE SNAPSHOT</span><h3>Cost & Repair Summary</h3></div><button type="button" onClick={() => setTab("estimate")}>Open Estimate →</button></header>
          <div className="jc-cost-grid">
            <ReadOnly label="Parts" value={money(partsTotal)} />
            <ReadOnly label="Labour" value={money(labourTotal)} />
            <ReadOnly label="Lines" value={`${parts.filter(p => p.part_no).length} parts · ${labours.filter(l => l.job_code).length} labour`} />
            <ReadOnly label="Grand Total" value={money(grandTotal)} />
          </div>
        </section>
      </>
    );
  }

  function renderJob() {
    return (
      <div className="jc-two-column">
        <section className="jc-card">
          <header><div><span className="jc-kicker">IDENTITY</span><h3>Job Card Information</h3></div></header>
          <div className="jc-form-grid">
            <Field label="Job Created Date"><input type="datetime-local" value={form.job_created_date} onChange={(e) => update("job_created_date", e.target.value)} disabled={!canEdit}/></Field>
            <Field label="Vehicle Inward By"><input value={form.vehicle_inward_by} onChange={(e) => update("vehicle_inward_by", e.target.value)} disabled={!canEdit}/></Field>
            <Field label="Insurance Company"><input value={form.insurance_company} onChange={(e) => update("insurance_company", e.target.value)} disabled={!canEdit}/></Field>
            <Field label="Policy No."><input value={form.policy_no} onChange={(e) => update("policy_no", e.target.value)} disabled={!canEdit}/></Field>
            <Field label="Status"><select value={form.jobcard_main_status} onChange={(e) => update("jobcard_main_status", e.target.value)} disabled={!canEdit}><option>Open</option><option>Closed</option></select></Field>
          </div>
        </section>
        <section className="jc-card">
          <header><div><span className="jc-kicker">VEHICLE</span><h3>Vehicle Snapshot</h3></div></header>
          {vehicle.registration_no ? (
            <div className="jc-vehicle-hero">
              {vehicle.image ? <img src={vehicle.image} alt="" /> : <div className="jc-car-placeholder">CAR</div>}
              <div><strong>{vehicle.registration_no}</strong><span>{vehicle.model_variant || "Vehicle"}</span><span>{customer.name || "Customer not available"}</span></div>
            </div>
          ) : (
            <Empty title="Select a vehicle" text="Choose a pending Gate In vehicle before creating a direct Job Card." />
          )}
        </section>
      </div>
    );
  }

  const selectedPanelLabel = ESTIMATE_PANELS.find(([key]) => key === estimatePanel)?.[1] || "";
  const selectedAction = ESTIMATE_ACTIONS.find(([key]) => key === estimateAction) || ESTIMATE_ACTIONS[0];

  function selectEstimatePanel(key) {
    setEstimatePanel(key);
    const label = ESTIMATE_PANELS.find(([panelKey]) => panelKey === key)?.[1] || "";
    setBuilderPart((p) => ({ ...p, description: label }));
    setBuilderLabour((l) => ({ ...l, job_code: selectedAction[2], description: `${selectedAction[3]} - ${label}`, hrs: selectedAction[4] }));
  }

  function selectEstimateAction(key) {
    setEstimateAction(key);
    const action = ESTIMATE_ACTIONS.find(([actionKey]) => actionKey === key) || ESTIMATE_ACTIONS[0];
    setBuilderLabour((l) => ({ ...l, job_code: action[2], description: `${action[3]}${selectedPanelLabel ? ` - ${selectedPanelLabel}` : ""}`, hrs: action[4] }));
  }

  function applyAiSuggestion(suggestion) {
    const category = String(suggestion.category || "other").toLowerCase();
    const actionMap = { broken: "replace", missing: "replace", dent: "dent", scratch: "repair", paint: "paint", glass: "replace" };
    const actionKey = actionMap[category] || "repair";
    const action = ESTIMATE_ACTIONS.find(([key]) => key === actionKey) || ESTIMATE_ACTIONS[1];
    setEstimateAction(actionKey);
    const label = suggestion.photo_caption || suggestion.caption || suggestion.note || "Detected damaged area";
    setBuilderPart((p) => ({ ...p, description: `${label} - ${category}` }));
    setBuilderLabour((l) => ({ ...l, job_code: action[2], description: `${action[3]} - ${label}`, hrs: action[4] }));
  }

  async function analyzeEstimatePhoto(photo) {
    if (!photo?.id || !payload.damageAiAnalyzeUrl || builderBusy) return;
    setBuilderBusy(true);
    try {
      const url = payload.damageAiAnalyzeUrl.replace("/0/", `/${photo.id}/`);
      const response = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" } });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) throw new Error(data.error || "AI analysis failed.");
      window.location.reload();
    } catch (err) {
      setError(err.message || "AI analysis failed.");
    } finally {
      setBuilderBusy(false);
    }
  }

  function addBuilderLines(type) {
    if (!canEdit || !estimatePanel) {
      setError(!canEdit ? "This Job Card is view-only." : "Select a vehicle panel first.");
      return;
    }
    if (type === "part" || type === "both") {
      if (builderPart.description.trim() || builderPart.part_no.trim()) {
        const row = { ...emptyPart(), ...builderPart, amount: Number(builderPart.qty || 0) * Number(builderPart.rate || 0) };
        setParts((rows) => [...rows.filter((r) => r.part_no || r.description), row]);
      }
    }
    if (type === "labour" || type === "both") {
      if (builderLabour.job_code.trim() || builderLabour.description.trim()) {
        const row = { ...emptyLabour(), ...builderLabour, amount: Number(builderLabour.hrs || 0) * Number(builderLabour.rate || 0) };
        setLabours((rows) => [...rows.filter((r) => r.job_code || r.description), row]);
      }
    }
    setMessage("Estimate line added.");
  }

  async function createPartRequisition() {
    if (!job.id || !canEdit || requisitionBusy) return;
    setRequisitionBusy(true);
    try {
      const response = await fetch(`/parts-requisitions/job/${job.id}/create/`, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify({}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status !== "success") throw new Error(data.message || "Part requisition create failed.");
      if (data.redirect_url) window.location.href = data.redirect_url;
    } catch (err) {
      setError(err.message || "Part requisition create failed.");
    } finally {
      setRequisitionBusy(false);
    }
  }

  function renderEstimate() {
    const showParts = tab === "estimate" || tab === "parts";
    const showLabour = tab === "estimate" || tab === "labour";
    const estimatePhotos = vehiclePhotoSlots.filter((p) => p.url);
    const currentPhoto = estimatePhotos[estimatePhotoIndex % Math.max(estimatePhotos.length, 1)];
    const suggestions = payload.damageAiSuggestions || payload.damage_ai_suggestions || [];
    const requisitions = payload.partRequisitions || payload.part_requisitions || [];

    return (
      <div className="jc-estimate-stack">
        {tab === "estimate" && (
          <section className="jc-card jc-estimate-builder">
            <header>
              <div><span className="jc-kicker">ESTIMATE BUILDER</span><h3>Create Estimate from Damage</h3></div>
              <span className="jc-badge">Panel → Action → Lines</span>
            </header>
            <div className="jc-builder-layout">
              <div className="jc-builder-photo">
                {currentPhoto ? (
                  <>
                    <img src={currentPhoto.url} alt={currentPhoto.caption || "Inspection photo"} />
                    <strong>{currentPhoto.caption}</strong>
                    <div className="jc-builder-photo-actions">
                      <button type="button" className="jc-btn secondary" onClick={() => setEstimatePhotoIndex((i) => (i - 1 + estimatePhotos.length) % estimatePhotos.length)}>←</button>
                      <span>{estimatePhotoIndex + 1} / {estimatePhotos.length}</span>
                      <button type="button" className="jc-btn secondary" onClick={() => setEstimatePhotoIndex((i) => (i + 1) % estimatePhotos.length)}>→</button>
                    </div>
                    {payload.damageAiAnalyzeUrl && <button type="button" className="jc-btn primary jc-builder-ai" onClick={() => analyzeEstimatePhoto(currentPhoto)} disabled={!canEdit || builderBusy}>{builderBusy ? "Analyzing…" : "Analyze This Photo with AI"}</button>}
                  </>
                ) : <Empty title="No inspection photos" text="Upload vehicle condition photos from Inspection before using the damage-based estimate builder." />}
              </div>
              <div className="jc-builder-controls">
                <Field label="Vehicle Panel">
                  <select value={estimatePanel} onChange={(e) => selectEstimatePanel(e.target.value)} disabled={!canEdit}>
                    <option value="">Select panel</option>
                    {ESTIMATE_PANELS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                  </select>
                </Field>
                <div className="jc-action-grid">
                  {ESTIMATE_ACTIONS.map(([key, label]) => <button key={key} type="button" className={`jc-action-btn ${estimateAction === key ? "active" : ""}`} onClick={() => selectEstimateAction(key)} disabled={!canEdit}>{label}</button>)}
                </div>
                <div className="jc-builder-two-col">
                  <Field label="Part No."><input value={builderPart.part_no} onChange={(e) => setBuilderPart((p) => ({ ...p, part_no: e.target.value }))} onBlur={() => { if (builderPart.part_no) lookupPartBuilder(); }} disabled={!canEdit} placeholder="Optional" /></Field>
                  <Field label="Part Qty"><input type="number" min="0" step="1" value={builderPart.qty} onChange={(e) => setBuilderPart((p) => ({ ...p, qty: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Part Description"><input value={builderPart.description} onChange={(e) => setBuilderPart((p) => ({ ...p, description: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Part Rate"><input type="number" min="0" step="0.01" value={builderPart.rate} onChange={(e) => setBuilderPart((p) => ({ ...p, rate: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Labour Code"><input value={builderLabour.job_code} onChange={(e) => setBuilderLabour((l) => ({ ...l, job_code: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Labour Hours"><input type="number" min="0" step="0.01" value={builderLabour.hrs} onChange={(e) => setBuilderLabour((l) => ({ ...l, hrs: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Labour Description"><input value={builderLabour.description} onChange={(e) => setBuilderLabour((l) => ({ ...l, description: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Labour Rate"><input type="number" min="0" step="0.01" value={builderLabour.rate} onChange={(e) => setBuilderLabour((l) => ({ ...l, rate: e.target.value }))} disabled={!canEdit}/></Field>
                  <Field label="Paint / Panel Type"><select value={builderLabour.paint_panel_type} onChange={(e) => setBuilderLabour((l) => ({ ...l, paint_panel_type: e.target.value }))} disabled={!canEdit}><option value="">No Paint Panel</option><option value="New">New Panel Painting</option><option value="Repair">Repair Panel Painting</option></select></Field>
                </div>
                <div className="jc-builder-buttons">
                  <button type="button" className="jc-btn secondary" onClick={() => addBuilderLines("part")} disabled={!canEdit}>+ Add Part</button>
                  <button type="button" className="jc-btn secondary" onClick={() => addBuilderLines("labour")} disabled={!canEdit}>+ Add Labour</button>
                  <button type="button" className="jc-btn primary" onClick={() => addBuilderLines("both")} disabled={!canEdit}>Add Part + Labour</button>
                </div>
              </div>
            </div>
            {suggestions.length > 0 && <div className="jc-ai-suggestions">
              <div className="jc-section-label">AI damage suggestions</div>
              {suggestions.map((s, i) => <div className="jc-ai-row" key={s.id || i}><div><strong>{s.category || "Damage"}</strong><span>{s.confidence != null ? ` ${s.confidence}%` : ""}</span><small>{s.note || s.photo_caption || "Potential damage detected"}</small></div><button type="button" className="jc-btn secondary" onClick={() => applyAiSuggestion(s)} disabled={!canEdit}>Use</button></div>)}
            </div>}
          </section>
        )}

        {showParts && <section className="jc-card">
          <header><div><span className="jc-kicker">ESTIMATE</span><h3>Parts</h3></div><button type="button" onClick={addPart} disabled={!canEdit}>+ Add Part</button></header>
          <div className="jc-table-wrap"><table className="jc-table"><thead><tr><th>Part No.</th><th>Description</th><th>Qty</th><th>Rate</th><th>Amount</th><th></th></tr></thead><tbody>{parts.map((row,i)=><tr key={`${row.id}-${i}`}><td><input value={row.part_no || ""} onChange={(e)=>updatePart(i,"part_no",e.target.value)} onBlur={()=>lookupPart(i)} disabled={!canEdit} placeholder="Search part no." /></td><td><input value={row.description || ""} onChange={(e)=>updatePart(i,"description",e.target.value)} disabled={!canEdit}/></td><td><input type="number" min="0" step="1" value={row.qty} onChange={(e)=>updatePart(i,"qty",e.target.value)} disabled={!canEdit}/></td><td><input type="number" min="0" step="0.01" value={row.rate} onChange={(e)=>updatePart(i,"rate",e.target.value)} disabled={!canEdit}/></td><td className="jc-number">{money(row.amount)}</td><td><button className="jc-icon-danger" type="button" onClick={()=>setParts((r)=>r.filter((_,x)=>x!==i))} disabled={!canEdit}>×</button></td></tr>)}</tbody></table></div>
          <div className="jc-total-bar"><span>Parts Total</span><strong>{money(partsTotal)}</strong></div>
        </section>}

        {showLabour && <section className="jc-card">
          <header><div><span className="jc-kicker">ESTIMATE</span><h3>Labour Operations</h3></div><button type="button" onClick={addLabour} disabled={!canEdit}>+ Add Labour</button></header>
          <div className="jc-table-wrap"><table className="jc-table"><thead><tr><th>Code</th><th>Operation</th><th>Hours</th><th>Rate</th><th>Paint</th><th>Amount</th><th></th></tr></thead><tbody>{labours.map((row,i)=><tr key={`${row.id}-${i}`}><td><input value={row.job_code || ""} onChange={(e)=>updateLabour(i,"job_code",e.target.value)} disabled={!canEdit}/></td><td><input value={row.description || ""} onChange={(e)=>updateLabour(i,"description",e.target.value)} disabled={!canEdit}/></td><td><input type="number" min="0" step="0.01" value={row.hrs} onChange={(e)=>updateLabour(i,"hrs",e.target.value)} disabled={!canEdit}/></td><td><input type="number" min="0" step="0.01" value={row.rate} onChange={(e)=>updateLabour(i,"rate",e.target.value)} disabled={!canEdit}/></td><td><select value={row.paint_panel_type || ""} onChange={(e)=>updateLabour(i,"paint_panel_type",e.target.value)} disabled={!canEdit}><option value="">—</option><option value="New">New</option><option value="Repair">Repair</option></select></td><td className="jc-number">{money(row.amount)}</td><td><button className="jc-icon-danger" type="button" onClick={()=>setLabours((r)=>r.filter((_,x)=>x!==i))} disabled={!canEdit}>×</button></td></tr>)}</tbody></table></div>
          <div className="jc-total-bar"><span>Labour Total</span><strong>{money(labourTotal)}</strong></div>
        </section>}

        <section className="jc-card jc-cost-summary">
          <header><div><span className="jc-kicker">TOTALS</span><h3>Estimate Summary</h3></div></header>
          <div className="jc-cost-grid">
            <ReadOnly label="Parts Total" value={money(partsTotal)} />
            <ReadOnly label="Labour Total" value={money(labourTotal)} />
            <ReadOnly label="GST (18%)" value={money(grandTotal * 0.18)} />
            <ReadOnly label="Net Total" value={money(grandTotal * 1.18)} />
          </div>
        </section>

        {job.id && tab === "estimate" && <section className="jc-card">
          <header><div><span className="jc-kicker">PARTS</span><h3>Part Requisitions</h3></div><button type="button" className="jc-btn primary" onClick={createPartRequisition} disabled={!canEdit || requisitionBusy || !parts.some((p)=>p.part_no)}>{requisitionBusy ? "Creating…" : "New Requisition"}</button></header>
          {requisitions.length ? <div className="jc-table-wrap"><table className="jc-table"><thead><tr><th>Requisition No</th><th>Requested</th><th>Priority</th><th>Status</th><th>Lines</th><th></th></tr></thead><tbody>{requisitions.map((r,i)=><tr key={r.id || i}><td>{r.requisition_no || "—"}</td><td>{r.requested_at_display || r.requested_at || "—"}</td><td>{r.priority || "Normal"}</td><td>{r.status || "Submitted"}</td><td>{r.line_count ?? r.lines_count ?? "—"}</td><td>{r.detail_url && <a className="jc-btn-link" href={r.detail_url}>View</a>}</td></tr>)}</tbody></table></div> : <p className="jc-muted-inline">No part requisition created yet. Requisitions can include estimated part lines.</p>}
        </section>}

        <section className="jc-grand-total"><span>Job Card Estimate</span><strong>{money(grandTotal)}</strong></section>
      </div>
    );
  }

  async function lookupPartBuilder() {
    const partNo = String(builderPart.part_no || "").trim().toUpperCase();
    if (!partNo) return;
    try {
      const response = await fetch(`/ajax/part-lookup/?item_code=${encodeURIComponent(partNo)}&t=${Date.now()}`, { credentials: "same-origin" });
      const data = await response.json();
      if (data.status !== "success") return;
      setBuilderPart((p) => ({ ...p, part_no: partNo, description: p.description || data.description || "", rate: data.rate || 0 }));
    } catch {
      // Existing row lookup remains the primary lookup path.
    }
  }

  function renderInspection() {
    const inventoryItems = [
      ["lh_mirror", "LH Mirror"],
      ["rh_mirror", "RH Mirror"],
      ["center_mirror", "Center Mirror"],
      ["jack", "Jack"],
      ["tool_kit", "Tool Kit"],
      ["frt_wiper", "Front Wiper"],
      ["rr_wiper", "Rear Wiper"],
      ["accessories", "Accessories"],
      ["stereo", "Stereo"],
      ["battery", "Battery"],
      ["number_plate", "Number Plate"],
    ];

    const currentFrame = rotationPhotos[rotationIndex];
    const currentFrameUrl = typeof currentFrame === "string" ? currentFrame : currentFrame?.url;

    return (
      <div className="jc-inspection-grid">
        <section className="jc-card jc-full">
          <header>
            <div><span className="jc-kicker">INWARD CONDITION</span><h3>Vehicle Inspection</h3></div>
            <span className="jc-badge">{job.updated_at_display || "Inspection"}</span>
          </header>
          <div className="jc-inspection-controls">
            <div className="jc-meter">
              <div className="jc-meter-head"><span>Fuel</span><strong>{form.fuel_percent}%</strong></div>
              <input type="range" min="0" max="100" value={form.fuel_percent} onChange={(e) => update("fuel_percent", e.target.value)} disabled={!canEdit}/>
              <small>{inspection.fuel_label || "Fuel level"}</small>
            </div>
            <div className="jc-meter">
              <div className="jc-meter-head"><span>CNG</span><strong>{form.cng_percent}%</strong></div>
              <input type="range" min="0" max="100" value={form.cng_percent} onChange={(e) => update("cng_percent", e.target.value)} disabled={!canEdit}/>
              <small>{inspection.cng_label || "CNG level"}</small>
            </div>
          </div>
          <div className="jc-form-grid jc-form-grid-3">
            <ReadOnly label="Inspection Date" value={payload.inspectionDate || job.updated_at_display} />
            <ReadOnly label="Inspected By" value={payload.loggedEmployeeName} />
            <ReadOnly label="Odometer" value={job.km ? `${job.km} Km` : "—"} />
          </div>
        </section>

        <section className="jc-card">
          <header><div><span className="jc-kicker">VEHICLE INVENTORY</span><h3>Items Received</h3></div></header>
          <div className="jc-inventory-counts">
            <Field label="Mud Flap"><input type="number" min="0" max="4" value={form.mud_flap_count} onChange={(e)=>update("mud_flap_count",e.target.value)} disabled={!canEdit}/></Field>
            <Field label="Floor Mat"><input type="number" min="0" max="10" value={form.floor_mat_count} onChange={(e)=>update("floor_mat_count",e.target.value)} disabled={!canEdit}/></Field>
          </div>
          <div className="jc-check-grid">
            {inventoryItems.map(([key, label]) => (
              <label key={key} className="jc-check">
                <input type="checkbox" checked={Boolean(form[key])} onChange={(e)=>update(key,e.target.checked)} disabled={!canEdit}/>
                <span>{label}</span>
              </label>
            ))}
          </div>
          <Field label="Inventory Remarks">
            <textarea rows="3" value={form.inventory_remarks} onChange={(e)=>update("inventory_remarks",e.target.value)} disabled={!canEdit} placeholder="Additional inventory remarks" />
          </Field>
        </section>

        <section className="jc-card">
          <header>
            <div><span className="jc-kicker">360° INSPECTION</span><h3>Vehicle Viewer</h3></div>
            {rotationPhotos.length > 0 && <button type="button" className="jc-btn secondary" onClick={()=>setShow360(true)}>Open Full View</button>}
          </header>
          {currentFrameUrl ? (
            <>
              <div
                className="jc-360-preview"
                onPointerDown={handle360PointerDown}
                onPointerMove={handle360PointerMove}
                onPointerUp={handle360PointerUp}
                onPointerCancel={handle360PointerUp}
                onWheel={(e)=>{e.preventDefault(); rotate360(e.deltaY || e.deltaX);}}
              >
                <img src={currentFrameUrl} alt="360 degree vehicle inspection" draggable="false" />
              </div>
              <div className="jc-360-caption">Drag left or right to rotate · <strong>{rotationIndex + 1}</strong>/{rotationPhotos.length} angles</div>
            </>
          ) : (
            <Empty title="No 360 photos" text="Upload the vehicle inspection views below to enable the 360 viewer." />
          )}
        </section>

        <section className="jc-card jc-full">
          <header>
            <div><span className="jc-kicker">VEHICLE CONDITION PHOTOS</span><h3>Inspection Photo Upload</h3></div>
            {payload.vehiclePhotoViewUrl && <a className="jc-btn secondary jc-btn-link" href={payload.vehiclePhotoViewUrl} target="_blank" rel="noreferrer">View All Photos</a>}
          </header>
          <p className="jc-muted-inline">Upload a photo against each required vehicle view. Re-uploading the same view replaces the existing photo.</p>
          <div className="jc-photo-grid">
            {vehiclePhotoSlots.length ? vehiclePhotoSlots.map((slot, index) => {
              const inputName = slot.inputName || slot.input_name || `vehicle_condition_photo_${slot.index || index + 1}`;
              const url = slot.url || slot.photoUrl || slot.photo?.url || "";
              return (
                <div className="jc-photo-slot" key={inputName}>
                  <div className="jc-photo-slot-head"><strong>{slot.index || index + 1}. {slot.caption || "Vehicle View"}</strong>{url && <span className="jc-badge success">Uploaded</span>}</div>
                  {url ? <a href={url} target="_blank" rel="noreferrer" className="jc-photo-preview"><img src={url} alt={slot.caption || "Vehicle inspection"}/><span>Open</span></a> : <div className="jc-photo-empty">No photo uploaded</div>}
                  <label className={`jc-file-button ${!canEdit ? "disabled" : ""}`}>
                    {url ? "Replace Photo" : "Upload Photo"}
                    <input
                      type="file"
                      accept="image/*"
                      disabled={!canEdit}
                      data-vehicle-photo-input={inputName}
                    />
                  </label>
                </div>
              );
            }) : <Empty title="No photo slots configured" text="The Django photo slot configuration was not included in the React payload." />}
          </div>
        </section>

        <section className="jc-card">
          <header>
            <div><span className="jc-kicker">DAMAGE MAP</span><h3>Vehicle Condition</h3></div>
            <button type="button" className="jc-btn secondary" onClick={()=>canEdit && update("damage_marks", [])} disabled={!canEdit || !(form.damage_marks || []).length}>Clear Marks</button>
          </header>
          {payload.damageImage ? (
            <div
              className="jc-damage-map interactive"
              onPointerDown={(e)=>{
                if (!canEdit || e.target !== e.currentTarget.querySelector("img")) return;
                const rect=e.currentTarget.getBoundingClientRect();
                const x=((e.clientX-rect.left)/rect.width)*100;
                const y=((e.clientY-rect.top)/rect.height)*100;
                e.currentTarget.dataset.startX=x;
                e.currentTarget.dataset.startY=y;
                e.currentTarget.setPointerCapture?.(e.pointerId);
              }}
              onPointerUp={(e)=>{
                if (!canEdit) return;
                const box=e.currentTarget, sx=Number(box.dataset.startX);
                const sy=Number(box.dataset.startY);
                if (!Number.isFinite(sx) || !Number.isFinite(sy)) return;
                const rect=box.getBoundingClientRect();
                const x=((e.clientX-rect.left)/rect.width)*100;
                const y=((e.clientY-rect.top)/rect.height)*100;
                const distance=Math.hypot(x-sx,y-sy);
                const mark=distance>1.5
                  ? {type:"scratch",x1:sx.toFixed(2),y1:sy.toFixed(2),x2:x.toFixed(2),y2:y.toFixed(2)}
                  : {type:"dent",x:x.toFixed(2),y:y.toFixed(2)};
                update("damage_marks", [...(form.damage_marks || []), mark]);
                delete box.dataset.startX; delete box.dataset.startY;
              }}
            >
              <img src={payload.damageImage} alt="Vehicle damage map" />
              {(form.damage_marks || []).map((mark,i)=>{
                const x=Number(mark.x ?? mark.x1 ?? 0), y=Number(mark.y ?? mark.y1 ?? 0);
                return <button key={i} type="button" className={`jc-damage-mark ${mark.type || "dent"}`} style={{left:`${x}%`,top:`${y}%`}} onClick={(e)=>{e.stopPropagation(); if(canEdit) update("damage_marks",form.damage_marks.filter((_,idx)=>idx!==i));}} title="Remove mark" />;
              })}
            </div>
          ) : <Empty title="No damage image" text="The legacy damage map image was not included in the React payload." />}
          <div className="jc-damage-legend"><span>Click = Dent</span><span>Drag = Scratch</span><span>Click a mark = Remove</span></div>
        </section>

        <section className="jc-card jc-full">
          <header><div><span className="jc-kicker">TYRE INVENTORY</span><h3>Tyre Details</h3></div></header>
          {tyres.length ? (
            <div className="jc-table-wrap">
              <table className="jc-table">
                <thead><tr><th>Position</th><th>Make</th><th>Size</th><th>Depth</th><th>Wheel Cap</th></tr></thead>
                <tbody>{tyres.map((t,i)=><tr key={`${t.position}-${i}`}>
                  <td><strong>{t.label || t.position}</strong></td>
                  <td><input value={t.make || ""} onChange={(e)=>setTyres(rows=>rows.map((r,x)=>x===i?{...r,make:e.target.value}:r))} disabled={!canEdit}/></td>
                  <td><input value={t.size || ""} onChange={(e)=>setTyres(rows=>rows.map((r,x)=>x===i?{...r,size:e.target.value}:r))} disabled={!canEdit}/></td>
                  <td><input type="number" step="0.1" value={t.depth ?? ""} onChange={(e)=>setTyres(rows=>rows.map((r,x)=>x===i?{...r,depth:e.target.value}:r))} disabled={!canEdit}/></td>
                  <td><select value={t.wheel_cap || "Y"} onChange={(e)=>setTyres(rows=>rows.map((r,x)=>x===i?{...r,wheel_cap:e.target.value}:r))} disabled={!canEdit}><option value="Y">Y</option><option value="N">N</option></select></td>
                </tr>)}</tbody>
              </table>
            </div>
          ) : <Empty title="No tyre records" text="Tyre details will appear here when available." />}
        </section>

        {show360 && currentFrameUrl && (
          <div className="jc-360-modal" role="dialog" aria-modal="true" aria-label="360 degree vehicle viewer" onClick={(e)=>{if(e.target===e.currentTarget)setShow360(false)}}>
            <div className="jc-360-dialog">
              <button type="button" className="jc-360-close" onClick={()=>setShow360(false)} aria-label="Close">×</button>
              <div
                className="jc-360-large"
                onPointerDown={handle360PointerDown}
                onPointerMove={handle360PointerMove}
                onPointerUp={handle360PointerUp}
                onPointerCancel={handle360PointerUp}
                onWheel={(e)=>{e.preventDefault(); rotate360(e.deltaY || e.deltaX);}}
              >
                <img src={currentFrameUrl} alt="360 degree vehicle view" draggable="false" />
              </div>
              <div className="jc-360-caption">Drag left or right to rotate · <strong>{rotationIndex + 1}</strong>/{rotationPhotos.length} angles</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  function renderClaim() {
    if (!claim) return <Empty title="Direct Job Card" text="This Job Card is not linked to an insurance claim." />;
    return (
      <div className="jc-two-column">
        <section className="jc-card">
          <header><div><span className="jc-kicker">CLAIM</span><h3>Claim Information</h3></div></header>
          <div className="jc-info-list">
            <ReadOnly label="Claim No." value={claim.claim_no} />
            <ReadOnly label="Claim Type" value={claim.claim_type_display} />
            <ReadOnly label="Stage" value={claim.stage_display} />
            <ReadOnly label="Insurance Company" value={claim.insurance_company} />
            <ReadOnly label="Policy No." value={claim.policy_no} />
            <ReadOnly label="Insurance Claim No." value={claim.ic_claim_no} />
            <ReadOnly label="Surveyor" value={claim.surveyor} />
          </div>
        </section>
        <section className="jc-card">
          <header><div><span className="jc-kicker">CLAIM FINANCIALS</span><h3>Financial Summary</h3></div></header>
          <div className="jc-cost-grid jc-cost-grid-2">
            <ReadOnly label="Estimated" value={money(claim.estimated_amount)} />
            <ReadOnly label="Approved" value={money(claim.approved_amount)} />
            <ReadOnly label="Deductible" value={money(claim.deductible)} />
            <ReadOnly label="Job Card Total" value={money(grandTotal)} />
          </div>
        </section>
      </div>
    );
  }

  async function postApprovalAction(url, body = null, options = {}) {
    if (!url || approvalBusy) return null;
    setApprovalBusy(true);
    setApprovalNotice("");
    setApprovalError("");
    try {
      const fetchOptions = {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrf(),
          "X-Requested-With": "XMLHttpRequest",
          ...(options.json ? { "Content-Type": "application/json" } : {}),
        },
        body: body
          ? options.json
            ? JSON.stringify(body)
            : body
          : undefined,
      };
      const response = await fetch(url, fetchOptions);
      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json().catch(() => ({}))
        : {};
      if (!response.ok || data.ok === false || data.status === "error") {
        throw new Error(data.error || data.message || `Request failed (${response.status})`);
      }
      return data;
    } catch (err) {
      setApprovalError(err.message || "Approval action failed.");
      return null;
    } finally {
      setApprovalBusy(false);
    }
  }

  async function reviewAiSuggestion(id, decision) {
    const urlTemplate = payload.damageAiReviewUrl;
    if (!id || !urlTemplate) return;
    const url = urlTemplate.replace("/0/", `/${id}/`);
    const data = await postApprovalAction(
      url,
      new URLSearchParams({ decision })
    );
    if (data) {
      const status = data.status || (decision === "Accepted" ? "Accepted" : "Rejected");
      setAiRows((rows) =>
        rows.map((row) => (String(row.id) === String(id) ? { ...row, status } : row))
      );
      setApprovalNotice(`AI suggestion ${status.toLowerCase()}.`);
    }
  }

  async function analyzeAiPhoto(photoId) {
    if (!photoId || !payload.damageAiAnalyzeUrl) return;
    const url = payload.damageAiAnalyzeUrl.replace("/0/", `/${photoId}/`);
    const data = await postApprovalAction(url);
    if (data) {
      setApprovalNotice("AI analysis completed. Refreshing suggestions…");
      window.location.reload();
    }
  }

  async function updateConsentLine(lineType, lineId, status) {
    if (!payload.customerConsentLineDecisionUrl || !lineId) return;
    const data = await postApprovalAction(
      payload.customerConsentLineDecisionUrl,
      new URLSearchParams({
        line_type: lineType,
        line_id: String(lineId),
        status,
      })
    );
    if (data) {
      const normalized = lineType === "part" ? "approvalPartRows" : "approvalLabourRows";
      if (normalized === "approvalPartRows") {
        setApprovalPartRows((rows) =>
          rows.map((row) => (String(row.id) === String(lineId) ? { ...row, approval_decision: status } : row))
        );
      } else {
        setApprovalLabourRows((rows) =>
          rows.map((row) => (String(row.id) === String(lineId) ? { ...row, approval_decision: status } : row))
        );
      }
      setApprovalNotice("Approval decision updated.");
    }
  }

  async function sendConsentLink() {
    if (!payload.sendPaidApprovalUrl) return;
    const data = await postApprovalAction(payload.sendPaidApprovalUrl);
    if (data?.redirect_url) {
      window.location.href = data.redirect_url;
      return;
    }
    setApprovalNotice("Customer consent link sent.");
    window.location.reload();
  }

  async function uploadApprovalEvidence() {
    if (!payload.uploadApprovalEvidenceUrl || !evidenceFile) {
      setApprovalError("Choose an evidence file first.");
      return;
    }
    const fd = new FormData();
    fd.append("evidence_type", evidenceType);
    fd.append("evidence_caption", evidenceCaption);
    fd.append("approval_evidence_file", evidenceFile);
    if (payload.latestApproval?.id) fd.append("approval_id", payload.latestApproval.id);

    const data = await postApprovalAction(payload.uploadApprovalEvidenceUrl, fd);
    if (data) {
      setApprovalNotice("Approval evidence uploaded.");
      setEvidenceFile(null);
      setEvidenceCaption("");
      window.location.reload();
    }
  }

  function openCustomerConsentLink() {
    const url = payload.manualCustomerApprovalUrl || payload.approvalLink || "";
    if (url) window.open(url, "_blank", "noopener,noreferrer");
    else setApprovalError("No customer consent link is available yet.");
  }

  function openManualWhatsApp() {
    const rawPhone = String(payload.manualWhatsappPhone || customer.mobile_no || customer.whatsapp_no || "");
    let phone = rawPhone.replace(/\D/g, "");
    if (phone.length === 10) phone = `91${phone}`;
    if (!phone) {
      setApprovalError("Customer WhatsApp/mobile number is required.");
      return;
    }
    const link = payload.manualCustomerApprovalUrl || payload.approvalLink || "";
    const message = [
      `Dear ${payload.manualCustomerName || customer.name || "Customer"},`,
      "",
      `Your vehicle ${payload.manualVehicleRegistration || vehicle.registration_no || ""} has been inspected and the repair estimate is ready.`,
      "",
      "Please review the customer consent link and reply after reviewing the estimate.",
      link ? `Consent Link: ${link}` : "",
      "",
      `Job Card: ${job.job_no || ""}`,
      "",
      "Thank you,",
      "MasterApp Bodyshop",
    ].filter(Boolean).join("\n");
    window.open(`https://wa.me/${phone}?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
  }

  async function copyConsentLink() {
    const url = payload.manualCustomerApprovalUrl || payload.approvalLink || "";
    if (!url) {
      setApprovalError("No customer consent link is available yet.");
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      setApprovalNotice("Consent link copied.");
    } catch {
      setApprovalError("Unable to copy the link.");
    }
  }

  function renderApproval() {
    const partsApproval = approvalPartRows;
    const labourApproval = approvalLabourRows;
    const latest = payload.latestApproval || null;
    const history = payload.approvalHistory || [];
    const attachments = payload.approvalAttachments || [];
    const photos = payload.approvalEditorPhotos || payload.approval_editor_photos || [];
    const pendingAi = aiRows.filter((row) => row.status === "Pending");
    const acceptedAi = aiRows.filter((row) => row.status === "Accepted");
    const rejectedAi = aiRows.filter((row) => row.status === "Rejected");
    const approvalLink = payload.manualCustomerApprovalUrl || payload.approvalLink || "";

    return (
      <div className="jc-phase3">
        {(approvalNotice || approvalError) && (
          <div className={`jc-phase3-alert ${approvalError ? "error" : "success"}`}>
            {approvalError || approvalNotice}
          </div>
        )}

        <section className="jc-card jc-phase3-hero">
          <div>
            <span className="jc-kicker">PHASE 3</span>
            <h3>Approval & Customer Consent</h3>
            <p>Review AI findings, assess estimate lines, send the consent link, and retain the customer's response/evidence.</p>
          </div>
          <div className="jc-phase3-status">
            <span className={`jc-status-pill ${String(latest?.status || "Not Sent").toLowerCase().replace(/\s+/g, "-")}`}>
              {latest?.status || "Not Sent"}
            </span>
            <small>{latest ? `Request #${latest.id}` : "No consent request yet"}</small>
          </div>
        </section>

        <section className="jc-card">
          <header>
            <div><span className="jc-kicker">AI DAMAGE REVIEW</span><h3>AI Findings</h3></div>
            <div className="jc-phase3-counts">
              <span>{aiRows.length} total</span>
              <span>{pendingAi.length} pending</span>
              <span>{acceptedAi.length} accepted</span>
              <span>{rejectedAi.length} rejected</span>
            </div>
          </header>

          <div className="jc-ai-photo-grid">
            {photos.length ? photos.map((photo) => {
              const photoRows = aiRows.filter((row) => String(row.photo_id) === String(photo.id));
              return (
                <article className="jc-ai-photo-card" key={photo.id}>
                  <div className="jc-ai-photo">
                    <img src={photo.url} alt={photo.caption || "Inspection"} />
                    {photoRows.map((row) => (
                      <span
                        key={row.id}
                        className={`jc-ai-box ${String(row.status).toLowerCase()}`}
                        style={{ left: `${row.x}%`, top: `${row.y}%`, width: `${row.width}%`, height: `${row.height}%` }}
                        title={`${row.category} · ${row.confidence}%`}
                      />
                    ))}
                  </div>
                  <div className="jc-ai-photo-footer">
                    <strong>{photo.caption || `Photo ${photo.id}`}</strong>
                    <button type="button" className="jc-btn tiny secondary" disabled={approvalBusy} onClick={() => analyzeAiPhoto(photo.id)}>
                      Analyze AI
                    </button>
                  </div>
                </article>
              );
            }) : (
              <Empty title="No inspection photos" text="Upload inspection photos in the Inspection tab before running AI analysis." />
            )}
          </div>

          <div className="jc-ai-list">
            {aiRows.length ? aiRows.map((row) => (
              <div className="jc-ai-row" key={row.id}>
                <div>
                  <strong>{row.category}</strong>
                  <span>{row.confidence}% confidence · {row.photo_caption || "Inspection photo"}</span>
                  <small>{row.note || "Potential visible damage detected."}</small>
                </div>
                <div className="jc-ai-actions">
                  <span className={`jc-decision ${String(row.status || "Pending").toLowerCase()}`}>{row.status || "Pending"}</span>
                  {row.status === "Pending" && (
                    <>
                      <button type="button" className="jc-btn tiny success" disabled={approvalBusy} onClick={() => reviewAiSuggestion(row.id, "Accepted")}>Accept</button>
                      <button type="button" className="jc-btn tiny danger" disabled={approvalBusy} onClick={() => reviewAiSuggestion(row.id, "Rejected")}>Reject</button>
                    </>
                  )}
                </div>
              </div>
            )) : (
              <div className="jc-muted">No AI suggestions have been generated yet.</div>
            )}
          </div>
        </section>

        <section className="jc-card">
          <header>
            <div><span className="jc-kicker">ASSESSMENT</span><h3>Parts & Labour Decisions</h3></div>
            <span className="jc-badge">{partsApproval.length + labourApproval.length} lines</span>
          </header>

          <div className="jc-approval-table-block">
            <h4>Parts</h4>
            <div className="jc-table-wrap">
              <table className="jc-table">
                <thead><tr><th>Part</th><th>Qty</th><th>Estimated</th><th>Revised</th><th>Decision</th><th>Remarks</th></tr></thead>
                <tbody>
  {partsApproval.length ? (
    partsApproval.map((row) => {
      const additional = Boolean(row.is_additional);
      console.log("Rendering part row:", row, "Additional:", additional);
      return (
        <tr
          key={row.id}
          className={additional ? "jc-additional-decision-row" : ""}
        >
          <td>
            <div className="jc-decision-line">
              {additional && (
                <span className="jc-additional-badge">
                  ⚡ ADDITIONAL
                </span>
              )}

              <strong>{row.part_no || "—"}</strong>
              <small>{row.description || ""}</small>
            </div>
          </td>

          <td>{row.qty ?? 0}</td>

          <td>{money(row.amount)}</td>

          <td>{money(row.approval_revised_amount)}</td>

          <td>
            <div className="jc-inline-decision">
              <select
                value={row.approval_decision || "None"}
                disabled={approvalBusy}
                onChange={(e) =>
                  updateConsentLine(
                    "part",
                    row.id,
                    e.target.value
                  )
                }
              >
                <option>None</option>
                <option>New</option>
                <option>Repair</option>
                <option>KO</option>
                <option>Reject</option>
              </select>
            </div>
          </td>

          <td>{row.approval_remarks || "—"}</td>
        </tr>
      );
    })
  ) : (
    <tr>
      <td colSpan="6">No parts found.</td>
    </tr>
  )}
</tbody>
              </table>
            </div>
          </div>

          <div className="jc-approval-table-block">
            <h4>Labour</h4>
            <div className="jc-table-wrap">
              <table className="jc-table">
                <thead><tr><th>Operation</th><th>Hours</th><th>Estimated</th><th>Revised</th><th>Decision</th><th>Remarks</th></tr></thead>
                <tbody>
                  {labourApproval.length ? labourApproval.map((row) => (
                    <tr key={row.id}>
                      <td><strong>{row.job_code || "—"}</strong><br/><small>{row.description || ""}</small></td>
                      <td>{row.labour_hrs ?? 0}</td>
                      <td>{money(row.amount)}</td>
                      <td>{money(row.approval_revised_amount)}</td>
                      <td>
                        <select value={row.approval_decision || "Approved"} disabled={approvalBusy} onChange={(e) => updateConsentLine("labour", row.id, e.target.value)}>
                          <option>Approved</option><option>Reject</option><option>KO</option>
                        </select>
                      </td>
                      <td>{row.approval_remarks || "—"}</td>
                    </tr>
                  )) : <tr><td colSpan="6">No labour found.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="jc-phase3-grid">
          <section className="jc-card">
            <header><div><span className="jc-kicker">CUSTOMER COMMUNICATION</span><h3>Consent Request</h3></div></header>
            <div className="jc-consent-card">
              <div className="jc-consent-actions">
                <button type="button" className="jc-btn primary" disabled={approvalBusy || !job.id} onClick={sendConsentLink}>
                  {approvalBusy ? "Working…" : latest ? "Resend Consent Link" : "Send Consent Link"}
                </button>
                <button type="button" className="jc-btn secondary" onClick={openCustomerConsentLink} disabled={!approvalLink}>Open Link</button>
                <button type="button" className="jc-btn secondary" onClick={copyConsentLink} disabled={!approvalLink}>Copy Link</button>
                <button type="button" className="jc-btn secondary" onClick={openManualWhatsApp}>WhatsApp</button>
              </div>
              <div className="jc-consent-details">
                <ReadOnly label="Customer" value={latest?.customer_name || payload.manualCustomerName || customer.name} />
                <ReadOnly label="Mobile" value={latest?.mobile_no || payload.manualWhatsappPhone || customer.mobile_no} />
                <ReadOnly label="Sent Via" value={latest?.communication_type || "—"} />
                <ReadOnly label="Responded" value={latest?.approval_date_display || "—"} />
              </div>
              <div className="jc-link-box">
                <span>Consent URL</span>
                <input value={approvalLink} readOnly placeholder="Send consent link to generate URL" />
              </div>
              {latest?.remarks && (
                <div className="jc-customer-remarks">
                  <strong>Latest customer response</strong>
                  <p>{latest.remarks}</p>
                </div>
              )}
            </div>
          </section>

          <section className="jc-card">
            <header><div><span className="jc-kicker">EVIDENCE</span><h3>Upload Approval Evidence</h3></div></header>
            {latest ? (
              <>
                <div className="jc-form-grid">
                  <Field label="Evidence Type">
                    <select value={evidenceType} onChange={(e) => setEvidenceType(e.target.value)} disabled={approvalBusy}>
                      <option value="WhatsApp">WhatsApp screenshot</option>
                      <option value="Email">Email</option>
                      <option value="SMS">SMS screenshot</option>
                      <option value="Other">Other</option>
                    </select>
                  </Field>
                  <Field label="Evidence File">
                    <input type="file" accept="image/*,.pdf,.txt,.eml" onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)} disabled={approvalBusy}/>
                  </Field>
                </div>
                <Field label="Caption">
                  <input value={evidenceCaption} onChange={(e) => setEvidenceCaption(e.target.value)} placeholder="Caption (optional)" disabled={approvalBusy}/>
                </Field>
                <button type="button" className="jc-btn primary" disabled={approvalBusy || !evidenceFile} onClick={uploadApprovalEvidence}>
                  Upload Evidence
                </button>
              </>
            ) : (
              <div className="jc-muted">Send a consent link first.</div>
            )}

            {attachments.length > 0 && (
              <div className="jc-evidence-list">
                {attachments.map((item) => (
                  <a key={item.id} href={item.url} target="_blank" rel="noreferrer">
                    <strong>{item.caption || item.evidence_type}</strong>
                    <span>{item.uploaded_at_display || ""}</span>
                  </a>
                ))}
              </div>
            )}
          </section>
        </section>

        <section className="jc-card">
          <header><div><span className="jc-kicker">RESPONSE HISTORY</span><h3>Customer Approval Timeline</h3></div><span className="jc-badge">{history.length} events</span></header>
          <div className="jc-history">
            {history.length ? history.map((event) => (
              <div className="jc-history-row" key={event.id}>
                <span className={`jc-status-pill ${String(event.status || "").toLowerCase().replace(/\s+/g, "-")}`}>{event.status}</span>
                <div><strong>{event.customer_name || "Customer"}</strong><small>{event.approval_date_display || event.created_at_display || ""}</small><p>{event.remarks || "No remarks recorded."}</p></div>
              </div>
            )) : <div className="jc-muted">No approval history yet.</div>}
          </div>
        </section>
      </div>
    );
  }
  function renderQuality() {
  const quality = payload.qualityCheck || {};

  const categories = quality.categories || [
    {
      number: 1,
      title: "Exterior",
      icon: "🚗",
      checks: [
        ["Body Panel Alignment", "pass"],
        ["Paint Finish", "pass"],
        ["Bumper Condition", "pass"],
        ["Door Alignment", "attention"],
        ["Lights & Indicators", "pass"],
        ["Glass & Windshield", "pass"],
      ],
    },
    {
      number: 2,
      title: "Paint & Body",
      icon: "🎨",
      checks: [
        ["Paint Match", "pass"],
        ["Surface Finish", "pass"],
        ["No Dents / Scratches", "pass"],
        ["Underbody Coating", "pass"],
        ["Rust Protection", "na"],
      ],
    },
    {
      number: 3,
      title: "Interior",
      icon: "💺",
      checks: [
        ["Dashboard", "pass"],
        ["Seats & Upholstery", "pass"],
        ["Floor Mats", "pass"],
        ["AC / Climate Control", "attention"],
        ["Infotainment System", "na"],
        ["Interior Lights", "pass"],
      ],
    },
    {
      number: 4,
      title: "Electrical",
      icon: "⚡",
      checks: [
        ["Headlights / Taillights", "pass"],
        ["Indicators / Horn", "pass"],
        ["Wipers", "pass"],
        ["Battery", "pass"],
        ["Charging System", "attention"],
      ],
    },
    {
      number: 5,
      title: "Mechanical",
      icon: "🔧",
      checks: [
        ["Brakes", "pass"],
        ["Engine Performance", "pass"],
        ["Tyre Condition", "attention"],
        ["Steering", "pass"],
        ["Suspension", "pass"],
        ["Fluid Levels", "pass"],
      ],
    },
    {
      number: 6,
      title: "Safety",
      icon: "🛡️",
      checks: [
        ["Seat Belts", "pass"],
        ["Airbags", "pass"],
        ["ABS", "pass"],
        ["ESC / Traction Control", "pass"],
        ["Fire Extinguisher", "na"],
      ],
    },
    {
      number: 7,
      title: "Road Test",
      icon: "◉",
      checks: [
        ["Steering Response", "pass"],
        ["Braking Performance", "pass"],
        ["Acceleration", "pass"],
        ["Noise / Vibration", "attention"],
        ["Overall Driving", "pass"],
      ],
    },
    {
      number: 8,
      title: "Documents & Accessories",
      icon: "📄",
      checks: [
        ["RC Book", "pass"],
        ["Insurance Copy", "pass"],
        ["Service History", "pass"],
        ["Spare Wheel & Tools", "pass"],
        ["Owner Manual", "pass"],
      ],
    },
  ];

  const statusLabel = {
    pass: "Pass",
    attention: "Attention",
    fail: "Fail",
    na: "N/A",
  };

  const statusIcon = {
    pass: "✓",
    attention: "!",
    fail: "×",
    na: "−",
  };

  const allChecks = categories.flatMap((category) => category.checks);

  const passCount = allChecks.filter(([, status]) => status === "pass").length;
  const attentionCount = allChecks.filter(
    ([, status]) => status === "attention"
  ).length;
  const failCount = allChecks.filter(([, status]) => status === "fail").length;
  const naCount = allChecks.filter(([, status]) => status === "na").length;

  const totalChecks = allChecks.length;
  const completedChecks = passCount + attentionCount + failCount;
  const qcCompleted =
    Boolean(payload.qualityCompleted) || Boolean(quality.completed);

  const photos =
    quality.photos ||
    payload.qualityPhotos ||
    payload.quality_photos ||
    [];

  return (
    <div className="qc-page">

      {/* HEADER */}
      <section className="qc-header">
        <div className="qc-title">
          <div className="qc-shield">◆</div>
          <div>
            <h2>Quality Inspection Checklist</h2>
            <p>
              Verify all quality checkpoints before closing the job card.
            </p>
          </div>
        </div>

        <div className="qc-date">
          <span>Inspection Date</span>
          <strong>
            {quality.inspectionDate ||
              payload.inspectionDate ||
              new Date().toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
          </strong>
        </div>
      </section>

      <div className="qc-layout">

        {/* MAIN CHECKLIST */}
        <div className="qc-main">

          <div className="qc-category-grid">
            {categories.map((category) => {
              const passed = category.checks.filter(
                ([, status]) => status === "pass"
              ).length;

              const total = category.checks.length;
              const percentage = Math.round((passed / total) * 100);

              return (
                <section className="qc-category" key={category.number}>

                  <div className="qc-category-header">
                    <div className="qc-category-title">
                      <span className="qc-category-icon">
                        {category.icon}
                      </span>

                      <strong>
                        {category.number}. {category.title}
                      </strong>
                    </div>

                    <span className="qc-count">
                      {passed} / {total}
                    </span>
                  </div>

                  <div className="qc-progress">
                    <div
                      style={{ width: `${percentage}%` }}
                    />
                  </div>

                  <div className="qc-check-list">
                    {category.checks.map(([name, status]) => (
                      <div className="qc-check" key={name}>

                        <span
                          className={`qc-status-icon ${status}`}
                        >
                          {statusIcon[status]}
                        </span>

                        <span className="qc-check-name">
                          {name}
                        </span>

                        <span
                          className={`qc-status-badge ${status}`}
                        >
                          {statusLabel[status]}
                        </span>

                      </div>
                    ))}
                  </div>

                </section>
              );
            })}

            {/* QC RESULT */}
            <section className="qc-result-card">

              <h3>QC Result</h3>

              <div className="qc-result-buttons">

                <button
                  type="button"
                  className={`qc-result-btn pass ${
                    qcCompleted ? "selected" : ""
                  }`}
                >
                  ✓ PASS
                </button>

                <button
                  type="button"
                  className="qc-result-btn fail"
                >
                  × FAIL
                </button>

              </div>

              <label className="qc-field">
                <span>Remarks</span>
                <textarea
                  defaultValue={
                    quality.remarks ||
                    "Left rear door alignment needs minor adjustment.\nRest all good."
                  }
                  placeholder="Enter QC remarks..."
                />
              </label>

              <div className="qc-photos-title">
                Photos / Attachments
              </div>

              <div className="qc-photo-list">

                {photos.slice(0, 3).map((photo, index) => (
                  <img
                    key={photo.id || index}
                    src={photo.url}
                    alt={`QC ${index + 1}`}
                  />
                ))}

                <button
                  type="button"
                  className="qc-add-photo"
                >
                  <span>＋</span>
                  Add Photo
                </button>

              </div>

            </section>
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <aside className="qc-sidebar">

          {/* VEHICLE */}
          <section className="qc-side-card">

            <h3>🚗 Vehicle Information</h3>

            <div className="qc-vehicle-photos">
              {(
                vehiclePhotoSlots.length
                  ? vehiclePhotoSlots
                  : rotationPhotos
              )
                .slice(0, 4)
                .map((photo, index) => (
                  <img
                    key={photo.id || index}
                    src={photo.url}
                    alt="Vehicle"
                  />
                ))}
            </div>

            <h4>
              {vehicle.make_model ||
                vehicle.model ||
                "Hyundai Creta 1.5 Petrol"}
            </h4>

            <div className="qc-info-grid">
              <div>
                <span>Reg. No.</span>
                <strong>
                  {vehicle.registration_no || "GJ05AB1234"}
                </strong>
              </div>

              <div>
                <span>Customer</span>
                <strong>
                  {customer.name || "Rahul Sharma"}
                </strong>
              </div>
            </div>

          </section>

          {/* JOB INFO */}
          <section className="qc-side-card">

            <h3>📋 Job Card Info</h3>

            <div className="qc-info-row">
              <span>Job Card No.</span>
              <strong>{job.job_no || "JC-10245"}</strong>
            </div>

            <div className="qc-info-row">
              <span>Claim No.</span>
              <strong>
                {claim?.claim_no || "CLM-45872"}
              </strong>
            </div>

            <div className="qc-info-row">
              <span>Advisor</span>
              <strong>
                {payload.advisorName || "Anil Shinde"}
              </strong>
            </div>

            <div className="qc-info-row">
              <span>Insurance</span>
              <strong>
                {payload.insuranceCompany || "HDFC ERGO"}
              </strong>
            </div>

          </section>

          {/* SUMMARY */}
          <section className="qc-side-card">

            <h3>◉ QC Summary</h3>

            <div className="qc-summary">

              <div
                className="qc-donut"
                style={{
                  "--qc-progress": `${
                    totalChecks
                      ? (completedChecks / totalChecks) * 100
                      : 0
                  }%`,
                }}
              >
                <strong>{totalChecks}</strong>
                <span>Total Checks</span>
              </div>

              <div className="qc-summary-list">

                <div>
                  <i className="pass" />
                  Pass
                  <strong>{passCount}</strong>
                </div>

                <div>
                  <i className="attention" />
                  Attention
                  <strong>{attentionCount}</strong>
                </div>

                <div>
                  <i className="fail" />
                  Fail
                  <strong>{failCount}</strong>
                </div>

                <div>
                  <i className="na" />
                  N/A
                  <strong>{naCount}</strong>
                </div>

              </div>

            </div>

          </section>

        </aside>
      </div>

      {/* FOOTER ACTIONS */}
      <div className="qc-actions">

        <button
          type="button"
          className="jc-btn secondary"
        >
          ↻ Reset
        </button>

        <button
          type="button"
          className="jc-btn secondary"
        >
          💾 Save
        </button>

        <button
          type="button"
          className="jc-btn primary"
        >
          ✓ Mark QC Completed
        </button>

      </div>

    </div>
  );
}
  function renderDelivery() {
    const ready = payload.closeReadyStatus || {};
    const readiness = [
      ["Work completed", Boolean(ready.work_completed ?? payload.repairCompleted)],
      ["Quality check", Boolean(ready.qc_done ?? payload.qualityCompleted)],
      ["Re-inspection", Boolean(ready.ri_done ?? payload.reinspectionDone)],
      ["Part entry", Boolean(ready.part_entry_complete)],
    ];
    const missing = readiness.filter(([, done]) => !done).map(([label]) => label);
    const checks = [
      ["Road Test", "road_test_done"],
      ["Washing", "washing_done"],
      ["Ready for Delivery", "ready_for_delivery"],
    ];
    const allChecks = checks.every(([, key]) => Boolean(form[key]));
    const canClose = Boolean(payload.canCloseJobcard) && allChecks && missing.length === 0;
    const isClosed = String(job.repair_status || "") === "Closed";

    return (
      <div className="jc-delivery-page">
        <section className="jc-card jc-delivery-hero">
          <div>
            <span className="jc-kicker">DELIVERY & CLOSURE</span>
            <h3>{isClosed ? "Job Card Closed" : "Final Delivery Gate"}</h3>
            <p className="jc-muted">Complete the workshop readiness checks and delivery checklist before changing the Job Card status to Closed.</p>
          </div>
          <span className={`jc-delivery-status ${isClosed ? "closed" : canClose ? "ready" : "pending"}`}>
            {isClosed ? "Closed" : canClose ? "Ready to Close" : "Pending"}
          </span>
        </section>

        <div className="jc-delivery-grid">
          <section className="jc-card">
            <header><div><span className="jc-kicker">READINESS</span><h3>Workshop Closure Gates</h3></div></header>
            <div className="jc-delivery-readiness-grid">
              {readiness.map(([label, done]) => (
                <div key={label} className={`jc-delivery-readiness ${done ? "done" : "pending"}`}>
                  <span>{done ? "✓" : "!"}</span>
                  <div><strong>{label}</strong><small>{done ? "Completed" : "Pending"}</small></div>
                </div>
              ))}
            </div>
            {missing.length > 0 && !isClosed && <div className="jc-delivery-warning">Complete: {missing.join(", ")}</div>}
          </section>

          <section className="jc-card">
            <header><div><span className="jc-kicker">FINAL AMOUNT</span><h3>Customer Payable / Job Total</h3></div></header>
            <div className="jc-delivery-total">{money(grandTotal)}</div>
            <div className="jc-delivery-financials">
              <ReadOnly label="Parts" value={money(partsTotal)} />
              <ReadOnly label="Labour" value={money(labourTotal)} />
              <ReadOnly label="Net Total" value={money(payload.netTotal ?? grandTotal)} />
            </div>
          </section>
        </div>

        <section className="jc-card">
          <header><div><span className="jc-kicker">HANDOVER</span><h3>Customer Handover Checklist</h3></div></header>
          <div className="jc-delivery-checks">
            {checks.map(([label, key]) => (
              <label key={key} className={`jc-delivery-check ${form[key] ? "checked" : ""}`}>
                <input type="checkbox" checked={Boolean(form[key])} onChange={(e) => update(key, e.target.checked)} disabled={!canEdit || isClosed} />
                <span>{label}</span>
                <small>{form[key] ? "Done" : "Pending"}</small>
              </label>
            ))}
            <div className="jc-delivery-check disabled"><span>Documents Returned</span><small>Not tracked in current Job Card model</small></div>
          </div>
        </section>

        <section className="jc-card jc-close-card">
          <header><div><span className="jc-kicker">CLOSURE</span><h3>Job Card Main Status</h3></div></header>
          <div className="jc-close-summary">
            <div><span>Current status</span><strong>{job.repair_status || "Open"}</strong></div>
            <div><span>System readiness</span><strong>{payload.canCloseJobcard ? "Ready" : "Blocked"}</strong></div>
            <div><span>Delivery checklist</span><strong>{allChecks ? "Complete" : `${checks.filter(([, key]) => !form[key]).map(([label]) => label).join(", ")} pending`}</strong></div>
          </div>
          {isClosed ? (
            <div className="jc-close-note">This Job Card is already closed. {payload.canReopenJobcard ? "Your role can re-open it by selecting the re-open status." : "Only Admin or Manager can re-open it."}</div>
          ) : (
            <div className="jc-close-controls">
              <Field label="Jobcard Main Status">
                <select value={form.jobcard_main_status} onChange={(e) => update("jobcard_main_status", e.target.value)} disabled={!canEdit || !payload.canCloseJobcard}>
                  <option value={job.repair_status || "Open"}>{job.repair_status || "Open"}</option>
                  <option value="Closed">Closed</option>
                </select>
              </Field>
              <div className={`jc-close-readiness ${canClose ? "ready" : "blocked"}`}>
                <strong>{canClose ? "Ready to close" : "Closure blocked"}</strong>
                <span>{canClose ? "All required gates and handover checks are complete." : "Complete the readiness gates and all three delivery checks."}</span>
              </div>
            </div>
          )}
        </section>
      </div>
    );
  }

  function renderTab() {
    if (tab === "overview") return renderOverview();
    if (tab === "job") return renderJob();
    if (tab === "estimate") return renderEstimate();
    if (tab === "inspection") return renderInspection();
    if (tab === "parts") return renderEstimate();
    if (tab === "labour") return renderEstimate();
    if (tab === "claim") return renderClaim();
    if (tab === "quality") return renderQuality();
    if (tab === "approval") return renderApproval();
    if (tab === "repair") return renderRepairProgress();
    return renderDelivery();
  }

  return (
    <div className="jobcard-react-page">
      <form onSubmit={saveJobCard}>
       
<header className="jc-header jc-header-compact">

  {/* Left: Job card identity */}
  <div className="jc-header-identity">

    <button
      type="button"
      className="jc-back"
      onClick={() => window.location.href = "/jobList/"}
      aria-label="Back to Job Cards"
    >
      ←
    </button>

    <div className="jc-job-info">
      <span className="jc-eyebrow">BODYSHOP / JOB CARD</span>

      <h1>
        {job.job_no ? `Job Card ${job.job_no}` : "New Job Card"}
      </h1>

      <p>
        {claim?.claim_no
          ? `Claim ${claim.claim_no}`
          : "Direct workshop job card"}
      </p>
    </div>

  </div>


  {/* Vehicle Snapshot */}
  <div className="jc-snapshot jc-vehicle-snapshot">

    <div className="jc-vehicle-image-wrap">
  {vehicle?.vehicle_image ? (
    <img
      src={vehicle.vehicle_image}
      alt={vehicle.registration_no || "Vehicle"}
      className="jc-vehicle-image"
    />
  ) : (
    <div className="jc-vehicle-image-placeholder">
      🚗
    </div>
  )}
</div>

    <div className="jc-snapshot-content">
      <span className="jc-snapshot-label">VEHICLE</span>

      <strong>
        {vehicle.registration_no || "Vehicle not selected"}
      </strong>

      <span>
        {vehicle.make || vehicle.manufacturer || ""}
        {vehicle.make && vehicle.model ? " · " : ""}
        {vehicle.model || ""}
      </span>
    </div>

  </div>


  {/* Customer Snapshot */}
<div className="jc-snapshot jc-customer-snapshot">

  <div className="jc-customer-avatar">
    {(customer?.name || "C")
      .split(" ")
      .map((part) => part[0])
      .slice(0, 2)
      .join("")
      .toUpperCase()}
  </div>

  <div className="jc-snapshot-content">
    <span className="jc-snapshot-label">CUSTOMER</span>

    <strong>
      {customer?.name || "Customer"}
    </strong>

    {customer?.mobile_no && (
      <span>{customer.mobile_no}</span>
    )}
  </div>

</div>


  {/* Advisor */}
  <div className="jc-mini-info">

    <span className="jc-snapshot-label">ADVISOR</span>

    <strong>
      {advisor?.name || payload?.advisorName || "Not Assigned"}
    </strong>

  </div>


  {/* Expected Delivery */}
  <div className="jc-mini-info jc-delivery-info">

    <span className="jc-snapshot-label">
      EXPECTED DELIVERY
    </span>

    <strong>
      {job?.expected_delivery_date
        ? new Date(job.expected_delivery_date).toLocaleDateString(
            "en-IN",
            {
              day: "2-digit",
              month: "short",
              year: "numeric",
            }
          )
        : payload?.expectedDelivery
        ? new Date(payload.expectedDelivery).toLocaleDateString(
            "en-IN",
            {
              day: "2-digit",
              month: "short",
              year: "numeric",
            }
          )
        : "Not Set"}
    </strong>

  </div>


  {/* Actions */}
  <div className="jc-actions jc-header-actions">

    {job.id && (
      <button
        type="button"
        className="jc-btn secondary"
        onClick={() =>
          window.open(
            payload.printUrl ||
            `/jobCard/${job.id}/print/`,
            "_blank"
          )
        }
      >
        Print
      </button>
    )}

    {job.id && (
      <button
        type="button"
        className="jc-btn secondary"
        onClick={() =>
          window.open(
            payload.estimatePrintUrl ||
            `/jobCard/${job.id}/estimate-print/`,
            "_blank"
          )
        }
      >
        Estimate
      </button>
    )}

    <button
      type="submit"
      className="jc-btn primary"
      disabled={!canEdit || saving}
    >
      {saving ? "Saving…" : "Save"}
    </button>

  </div>

</header>
{payload?.second_approval_pending && (
  <section className="jc-additional-approval jc-approval-attention">
    {/* Animated attention indicator */}
    <div className="jc-approval-alert-icon">
      <span>!</span>
    </div>

    {/* Main content */}
    <div className="jc-additional-approval-main">
      <span className="jc-snapshot-label">
        ADDITIONAL APPROVAL
      </span>

      <h3>Surveyor / Additional Approval</h3>

      <p>
        Advisor decision is required for additional work.
      </p>

      <span className="jc-approval-pending-label">
        <span className="jc-pulse-dot"></span>
        Pending your review
      </span>
    </div>

    {/* Approval statistics */}
    <div className="jc-additional-approval-meta">

      <span>
        <strong>
          {payload.additional_approval_parts?.length || 0}
        </strong>
        Parts
      </span>

      <span>
        <strong>
          {payload.additional_approval_labours?.length || 0}
        </strong>
        Labour
      </span>

      <span className="approval-approved">
        <strong>
          {payload.additional_approval_approved_count || 0}
        </strong>
        Approved
      </span>

      <span className="approval-rejected">
        <strong>
          {payload.additional_approval_rejected_count || 0}
        </strong>
        Rejected
      </span>

      <span className="approval-pending">
        <strong>
          {payload.additional_approval_pending_count || 0}
        </strong>
        Pending
      </span>

    </div>

    {/* CTA */}
    <button
      type="button"
      className="jc-approval-details-btn"
      onClick={() => setTab("approval")}
    >
      Show Details
      <span>→</span>
    </button>

  </section>
)}
        {(message || error) && <div className={`jc-alert ${error ? "error" : "success"}`}>{error || message}</div>}

        {locked && <div className="jc-lock-banner">This Job Card is closed and is view-only.</div>}

        {!job.id && (
          <section className="jc-card jc-create-card">
            <header><div><span className="jc-kicker">CREATE</span><h3>Vehicle Selection</h3></div></header>
            <div className="jc-form-grid">
              <Field label="Vehicle" hint="Pending Gate In vehicles for the current branch">
                <select value={form.direct_vehicle} onChange={(e)=>update("direct_vehicle",e.target.value)} disabled={!canEdit}>
                  <option value="">Select vehicle</option>
                  {(payload.directVehicles || []).map(v=><option key={v.id} value={v.id}>{v.text}</option>)}
                </select>
              </Field>
              <Field label="Gate In Entry"><input value={form.gate_entry_id} onChange={(e)=>update("gate_entry_id",e.target.value)} disabled /></Field>
            </div>
          </section>
        )}

        <nav className="jc-tabs" aria-label="Job Card sections">
          {TABS.map(([key, label]) => (
            <button key={key} type="button" className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>
          ))}
        </nav>

        <main className="jc-content">{renderTab()}</main>

        <footer className="jc-footer">
          <div><strong>{money(grandTotal)}</strong><span>Current estimate</span></div>
          <div className="jc-footer-actions">
            <button type="button" className="jc-btn secondary" onClick={() => window.scrollTo({top:0,behavior:"smooth"})}>Back to top</button>
            <button type="submit" className="jc-btn primary" disabled={!canEdit || saving}>{saving ? "Saving…" : "Save Job Card"}</button>
          </div>
        </footer>
      </form>
    </div>
  );
}
