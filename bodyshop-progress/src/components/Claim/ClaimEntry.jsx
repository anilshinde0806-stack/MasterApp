import { useEffect, useMemo, useState } from "react";
import { getCSRFToken } from "../../utils/csrf";
import "./ClaimEntry.css";

const payload = window.__CLAIM_ENTRY__ || {};

export default function ClaimEntry() {
  console.log("🔥 CLAIM REACT PHASE 5 LOADED", payload.isAdminUser);
  const [form, setForm] = useState(payload.values || {});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [files, setFiles] = useState({});
  const [expandedSections, setExpandedSections] = useState({ intimation: payload.currentStage === 3, survey: payload.currentStage === 5, approval: payload.currentStage === 6 });
  const [expandedStages, setExpandedStages] = useState(new Set());
  const toggleCompletedStage = (stageNumber) => {
    setExpandedStages((current) => {
      const next = new Set(current);
      if (next.has(stageNumber)) next.delete(stageNumber);
      else next.add(stageNumber);
      return next;
    });
  };
  const completedStageNumbers = (payload.stages || [])
    .filter((stage) => stage.number < (payload.currentStage || 1))
    .map((stage) => stage.number);
  const allCompletedExpanded =
    completedStageNumbers.length > 0 &&
    completedStageNumbers.every((number) => expandedStages.has(number));
  const toggleAllCompleted = () => {
    setExpandedStages(
      allCompletedExpanded ? new Set() : new Set(completedStageNumbers)
    );
  };
  const [assessmentModalOpen, setAssessmentModalOpen] = useState(false);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentSaving, setAssessmentSaving] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [assessment, setAssessment] = useState({ parts: [], labours: [], job_no: "" });
  const toggleSection = (section) => setExpandedSections((current) => ({ ...current, [section]: !current[section] }));
  const openAssessment = async () => {
    if (!payload.jobcardId) return;
    setAssessmentModalOpen(true); setAssessmentLoading(true); setAssessmentError("");
    try {
      const response = await fetch(`/api/jobcard/${payload.jobcardId}/assessment/?t=${Date.now()}`, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Unable to load assessment entries.");
      setAssessment(await response.json());
    } catch (err) { setAssessmentError(err.message); } finally { setAssessmentLoading(false); }
  };
  const saveAssessment = async () => {
    const requiredRows = [
      ...(assessment.parts || []).filter((item) => item.is_new).map((item) => ({ item, fields: [["part_no", "Part no"], ["description", "Part description"], ["amount", "Part amount"]] })),
      ...(assessment.labours || []).filter((item) => item.is_new).map((item) => ({ item, fields: [["job_code", "Job code"], ["description", "Job description"], ["amount", "Labour amount"]] })),
    ];
    for (const row of requiredRows) {
      for (const [key, label] of row.fields) {
        if (!String(row.item[key] ?? "").trim()) {
          setAssessmentError(`${label} cannot be blank.`);
          return;
        }
      }
    }
    let assessmentPayload = assessment;
    if (String(assessment.job_no || "").startsWith("JOB-")) {
      const jobNo = window.prompt("Enter DMS Jobcard No", "");
      if (!jobNo || !jobNo.trim()) {
        setAssessmentError("DMS Jobcard No is required before saving assessment.");
        return;
      }
      assessmentPayload = { ...assessment, job_no: jobNo.trim() };
      setAssessment(assessmentPayload);
    }
    setAssessmentSaving(true); setAssessmentError("");
    try {
      const response = await fetch(`/api/jobcard/${payload.jobcardId}/assessment/save/`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() }, body: JSON.stringify(assessmentPayload) });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.status !== "success") throw new Error(result.message || "Unable to save assessment.");
      setAssessmentModalOpen(false); setMessage("Assessment saved successfully.");
    } catch (err) { setAssessmentError(err.message); } finally { setAssessmentSaving(false); }
  };
  const deleteAssessmentFile = async () => {
    if (!window.confirm("Delete the saved Assessment Document?")) return;
    const response = await fetch(`/claim/${payload.claimId}/assessment-file/delete/`, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": getCSRFToken() } });
    if (!response.ok) { setError("Unable to delete the Assessment Document."); return; }
    update("assessment_file", ""); setFiles((current) => ({ ...current, assessment_file: [] })); setMessage("Assessment Document deleted.");
  };
  const printAssessmentReport = () => {
    if (!payload.jobcardId) {
      setAssessmentError("Please open an assessment first.");
      return;
    }
    window.open(`/jobCard/${payload.jobcardId}/assessment-print/`, "_blank", "noopener,noreferrer");
  };
  useEffect(() => {
    const handlePrintClick = (event) => {
      const button = event.target.closest("button");
      if (button?.textContent?.includes("Print Assessment")) {
        event.preventDefault();
        printAssessmentReport();
      }
    };
    document.addEventListener("click", handlePrintClick);
    return () => document.removeEventListener("click", handlePrintClick);
  }, [payload.jobcardId]);

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const selectedVehicle = (payload.options?.vehicles || []).find((item) => String(item.id) === String(form.vehicle));
  const selectedInsurance = (payload.options?.insuranceCompanies || []).find((item) => String(item.id) === String(form.insurance_company));
  const currentStageName = payload.stages?.find((stage) => stage.number === payload.currentStage)?.label || "Claim Created";
  const stageCaption = payload.currentStage >= 6 ? "Record insurance approval and upload the assessment document." : payload.currentStage >= 5 ? "Capture survey information and keep the inspection details up to date." : payload.currentStage >= 4 ? "Enter the accident and insurance information to initiate the claim process." : payload.currentStage === 3 ? "Create the job card estimate and send it to Claim Intimation when ready." : "Enter the basic claim details to initiate the insurance claim process.";
  const stageIcon = payload.currentStage >= 6 ? "✓" : payload.currentStage >= 4 ? "⚠" : payload.currentStage === 3 ? "▣" : "▤";
  useEffect(() => {
    const current = document.querySelector(`[data-claim-stage="${payload.currentStage}"]`);
    if (current) setTimeout(() => current.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" }), 250);
  }, []);
  useEffect(() => { const openVehicle = (event) => { if (event.target.closest(".claim-vehicle-preview") && selectedVehicle?.id) window.location.href = `/vehicle/${selectedVehicle.id}/`; }; document.addEventListener("click", openVehicle); return () => document.removeEventListener("click", openVehicle); }, [selectedVehicle?.id]);
  const handleVehicleChange = async (vehicleId) => {
    if (!vehicleId) { update("vehicle", ""); return; }
    const response = await fetch(`/ajax/check-open-claim/?vehicle_id=${vehicleId}`, { credentials: "same-origin" });
    const result = await response.json();
    if (result.exists) {
      update("vehicle", "");
      setError(`Open claim already exists: ${result.claim_no}`);
      return;
    }
    setError("");
    update("vehicle", vehicleId);
  };

  const submit = async (event, advance = false) => {
    event.preventDefault();
    setSaving(true); setError(""); setMessage("");
    if (payload.currentStage >= 4 && (!form.accident_date || !form.intimation_date || !form.insurance_company || !String(form.policy_no || "").trim() || !String(form.ic_claim_no || "").trim())) {
      setError("Please complete Accident Date, Claim Intimation Date, Insurance Company, Policy No, and Insurance Claim No.");
      setSaving(false); return;
    }
    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, key === "reinspection_done" ? (value ? "1" : "0") : (value ?? "")));
    Object.entries(files).forEach(([key, selected]) => selected.forEach((file) => data.append(key, file)));
    try {
      const response = await fetch(payload.submitUrl || "/claim/save/", {
        method: "POST", credentials: "same-origin",
        headers: { "X-CSRFToken": getCSRFToken() }, body: data,
      });
      if (response.redirected) {
        if (advance && payload.isEdit) {
          const autoAdvancedStage = [4, 5].includes(payload.currentStage);
          window.location.href = autoAdvancedStage ? payload.submitUrl : (payload.stageUrls?.next || response.url);
        } else {
          window.location.href = response.url || "/claimList/";
        }
        return;
      }
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.status === "error") {
        const validationErrors = result.errors
          ? Object.values(result.errors).flat().join(" ")
          : "Unable to save claim.";
        throw new Error(result.message || validationErrors);
      }
      if (advance && payload.isEdit) {
        const autoAdvancedStage = [4, 5].includes(payload.currentStage);
        window.location.href = autoAdvancedStage ? payload.submitUrl : (payload.stageUrls?.next || payload.submitUrl);
      } else if (payload.isEdit) {
        window.location.href = payload.submitUrl;
      } else {
        window.location.href = "/claimList/";
      }
    } catch (err) { setError(err.message); } finally { setSaving(false); }
  };

  const moveStage = async (direction) => {
    if (payload.isLocked) return;
    if (
  direction === "back" &&
  payload.currentStage >= 8 &&
  payload.hasRepairProgressData === true &&
  payload.isAdminUser !== true
) {
  setError(
    "Cannot move previous. Repair progress has started. First clear progress rows and uploaded progress photos from Work Allocation."
  );
  return;
}
    if (direction === "back" && !window.confirm("Move claim to previous stage?")) return;
    if (direction === "next") {
      const missing = [];
      const value = (key) => String(form[key] ?? "").trim();
      if (payload.currentStage === 1 && !value("employee")) missing.push("Advisor");
      if (payload.currentStage === 3) {
        if (!value("employee")) missing.push("Select Advisor First");
        if (!value("intimation_date")) missing.push("Claim Intimation Date");
        if (!value("insurance_company")) missing.push("Insurance Company");
        if (!value("policy_no")) missing.push("Policy No");
        if (!value("ic_claim_no")) missing.push("Insurance Claim No");
      }
      if (payload.currentStage === 4) {
        if (!value("survey_date")) missing.push("Survey Date");
        if (!value("surveyor")) missing.push("Surveyor");
        if (!value("survey_status")) missing.push("Survey Status");
      }
      if (payload.currentStage === 5) {
        if (!value("insurance_approval_date")) missing.push("Insurance Approval Date");
        if (!value("assessment_file") && !(files.assessment_file?.length)) missing.push("Assessment File");
      }
      if (payload.currentStage === 7 && payload.hasRepairProgressStarted !== true) missing.push("Start at least one progress stage from Work Allocation");
      if (payload.currentStage === 8) missing.push("Work Completed must be marked from Work Allocation");
      if (payload.currentStage === 10 && form.reinspection_done !== true) missing.push("Complete Re Inspection");
      if (missing.length) { setError(`Cannot move next. Missing: ${missing.join(", ")}`); return; }
    }
    setSaving(true); setError("");
    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, key === "reinspection_done" ? (value ? "1" : "0") : (value ?? "")));
    Object.entries(files).forEach(([key, selected]) => selected.forEach((file) => data.append(key, file)));
    try {
      const response = await fetch(payload.submitUrl, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": getCSRFToken() }, body: data });
      if (!response.ok) throw new Error("Unable to save claim details before changing stage.");
      window.location.href = payload.stageUrls?.[direction];
    } catch (err) { setError(err.message); setSaving(false); }
  };

  return <main className="claim-react-page">
    <header className="claim-react-header">
      <button type="button" className="claim-header-back" onClick={() => window.location.href = "/claimList/"} aria-label="Back to claim list">←</button>
      <div className="claim-header-title"><h1>Claim Entry</h1><p>Manage and track the claim processing stages</p></div>
      <div className="claim-header-spacer" />
      {payload.isEdit && <div className="claim-header-number"><span>Claim No.</span><strong>▣　{form.claim_no || "-"}</strong></div>}
      <span className="claim-header-status"><i />{payload.isLocked ? "Closed" : "In Progress"}</span>
      <button type="button" className="claim-header-menu" aria-label="More options">⋮</button>
    </header>

    

    <section className="claim-progress-strip">
  <div className="claim-progress-title">
    ⌁ <span>Claim Stages</span>
  </div>

  <div className="claim-stage-strip">
    {(payload.stages || []).map((stage) => {
      const done = payload.currentStage > stage.number;
      const current = payload.currentStage === stage.number;

      return (
        <button
          type="button"
          className={`claim-stage ${done ? "done" : current ? "active" : "pending"}`}
          data-claim-stage={stage.number}
          key={stage.number}
          onClick={() => {
            if (done) {
              toggleCompletedStage(stage.number);
            }
          }}
          disabled={!done}
          title={
            done
              ? `View ${stage.label} details`
              : current
                ? "Current stage"
                : "Pending stage"
          }
        >
          <span className="claim-stage-dot">
            {done ? "✓" : current ? "⚒" : stage.number}
          </span>

          <small>
            {done ? "Completed" : current ? "In Progress" : "Pending"}
          </small>

          <b>{stage.label}</b>

          {done && (
            <em className="claim-stage-review-hint">
              {expandedStages.has(stage.number) ? "Hide" : "View"}
            </em>
          )}
        </button>
      );
    })}
  </div>
</section>
    
    


    <div className="claim-react-layout">
      <div className="claim-react-main-column">
      
      <section className="claim-current-stage-hero"><div className="claim-current-stage-icon">{stageIcon}</div><div className="claim-current-stage-copy"><span>CURRENT STAGE</span><h3>{currentStageName}</h3></div><div className="claim-stage-progress"><small>Stage Progress</small><b>{payload.currentStage || 1} of {payload.stages?.length || 14}</b><i><em style={{width:`${((payload.currentStage || 1) / (payload.stages?.length || 14)) * 100}%`}} /></i></div><div className="claim-stage-action-buttons"><button type="button" onClick={() => moveStage("back")} disabled={saving || payload.isLocked || payload.currentStage <= 1}>← Previous</button><button type="button" className="primary" onClick={() => moveStage("next")} disabled={saving || payload.isLocked || payload.currentStage >= 14}>{saving ? "Saving..." : `Next: ${payload.nextStageLabel || "Continue"} →`}</button></div></section>      
      {error && <div className="claim-react-error">{error}</div>}{message && <div className="claim-react-success">{message}</div>}
      <form onSubmit={(event) => submit(event, false)} className={`claim-react-card claim-stage-${payload.currentStage || 1}`}>
        {(payload.stages || []).some((stage) => stage.number < (payload.currentStage || 1)) && (
      <section className="claim-completed-history">
        <div className="claim-history-heading">
          <div>
            <span>WORKFLOW HISTORY</span>
            <h2>Completed Stages <small>(Click to view details)</small></h2>
          </div>
          <button type="button" className="claim-history-expand-all" onClick={toggleAllCompleted}>
            {allCompletedExpanded ? "Collapse All" : "Expand All"} <b>{allCompletedExpanded ? "⌃" : "⌄"}</b>
          </button>
        </div>
        <div className="claim-history-list">
          {(payload.stages || [])
            .filter((stage) => stage.number < (payload.currentStage || 1))
            .map((stage) => {
              const expanded = expandedStages.has(stage.number);
              const history = (payload.stageHistory || [])
                .filter((item) => Number(item.stage) === Number(stage.number))
                .slice(-1)[0] || {};
              return (
                <div className={`claim-history-item ${expanded ? "expanded" : ""}`} key={stage.number}>
                  <button
                    type="button"
                    className="claim-history-row"
                    onClick={() => toggleCompletedStage(stage.number)}
                    aria-expanded={expanded}
                  >
                    <span className="claim-history-check">✓</span>
                    <span className="claim-history-stage">
                      <strong>Stage {stage.number} — {stage.label}</strong>
                      <small>{stageHistoryDescription(stage.number)}</small>
                    </span>
                    <span className="claim-history-meta">
                      {history.changedAt || "Completed"}{history.changedBy ? ` · ${history.changedBy}` : ""}
                    </span>
                    <span className="claim-history-chevron">{expanded ? "⌃" : "⌄"}</span>
                  </button>
                  {expanded && (
                    <CompletedStageDetails
                      stage={stage.number}
                      form={form}
                      payload={payload}
                      history={history}
                    />
                  )}
                </div>
              );
            })}
        </div>
      </section>
    )}
        <StageWorkspace stage={payload.currentStage} payload={payload} form={form} update={update} setFiles={setFiles} disabled={payload.isLocked} />

        
      {payload.currentStage <= 6 && (
        <>
      <div className="claim-input-section-heading"><span className="claim-input-section-icon">▣</span><div><h3>Claim Information</h3><p>Review and update the information required for this stage.</p></div></div>
        <div className="claim-react-grid">
          <Field label="Claim No" value={form.claim_no} readOnly />
          <Select label="Claim Type" value={form.claim_type} options={payload.options?.claimTypes} onChange={(v) => update("claim_type", v)} />
          <Field label="Claim Created Date" type="datetime-local" value={form.claim_created_date} onChange={(v) => update("claim_created_date", v)} readOnly={payload.isEdit} />
          <Select label="Vehicle" value={form.vehicle} options={payload.options?.vehicles} onChange={handleVehicleChange} placeholder="Search vehicle..." searchable disabled={payload.isLocked} />
          <Select label="Advisor" value={form.employee} options={payload.options?.employees} onChange={(v) => update("employee", v)} disabled={!payload.canChangeAdvisor} />
          
          {payload.currentStage >= 3 && <div className="claim-form-subsection"><button type="button" className="claim-form-subsection-heading" onClick={() => toggleSection("intimation")}><span className="claim-form-subsection-icon">⚠</span><span><h3>Claim Intimation</h3><p>Enter accident and insurance details for the claim.</p></span><b>{expandedSections.intimation ? "⌃" : "⌄"}</b></button>{expandedSections.intimation && <>
            <Field label="Accident Date" type="date" value={form.accident_date} onChange={(v) => update("accident_date", v)} disabled={payload.isLocked} />
            <Field label="Claim Intimation Date" type="datetime-local" value={form.intimation_date} onChange={(v) => update("intimation_date", v)} disabled={payload.isLocked} />
            <Select label="Insurance Company" value={form.insurance_company} options={payload.options?.insuranceCompanies} onChange={(v) => update("insurance_company", v)} disabled={payload.isLocked} />
            <Field label="Policy No" value={form.policy_no} onChange={(v) => update("policy_no", v)} disabled={payload.isLocked} />
            <Field label="Insurance Claim No" value={form.ic_claim_no} onChange={(v) => update("ic_claim_no", v)} disabled={payload.isLocked} />
            <div className="claim-document-upload"><span>Claim Documents</span>{(payload.options?.documentSlots || []).map((slot) => { const selected = files[slot.inputName]?.length > 0; const saved = slot.documents?.length > 0; return <label key={slot.inputName} className={selected || saved ? "document-uploaded" : ""}><div className="document-slot-heading"><small>{slot.documentType}</small>{(selected || saved) && <i className="document-success" title="Document uploaded">✓</i>}</div><input type="file" multiple onChange={(event) => setFiles((current) => ({ ...current, [slot.inputName]: Array.from(event.target.files || []) }))} disabled={payload.isLocked} />{selected && <em>{files[slot.inputName][0].name}<button type="button" className="document-delete" onClick={(event) => { event.preventDefault(); event.stopPropagation(); setFiles((current) => ({ ...current, [slot.inputName]: [] })); }} title="Remove selected file">🗑</button></em>}{saved && !selected && <em><a href={slot.documents[0].url} target="_blank" rel="noreferrer">View</a><span> · Replace using file picker</span><button type="button" className="document-delete" onClick={(event) => { event.preventDefault(); event.stopPropagation(); setFiles((current) => ({ ...current, [slot.inputName]: [] })); }} title="Clear document">🗑</button></em>}</label>; })}</div>
          </>}</div>}
          {payload.currentStage >= 5 && <div className="claim-form-subsection claim-survey-subsection"><button type="button" className="claim-form-subsection-heading" onClick={() => toggleSection("survey")}><span className="claim-form-subsection-icon survey">5</span><span><h3>Survey Entry</h3><p>Enter survey details and upload the survey report from the insurance surveyor.</p></span><b>{expandedSections.survey ? "⌃" : "⌄"}</b></button>{expandedSections.survey && <div className="claim-survey-layout">
            <section className="claim-survey-panel"><h4>▣ Survey Information</h4><div className="claim-survey-fields">
              <Select label="Surveyor Name" value={form.surveyor} options={payload.options?.surveyors} onChange={(v) => update("surveyor", v)} disabled={payload.isLocked} />
              <Field label="Survey Agency" value={form.survey_agency || ""} onChange={(v) => update("survey_agency", v)} disabled={payload.isLocked} placeholder="Survey agency" />
              <Field label="Survey Date" type="datetime-local" value={form.survey_date} onChange={(v) => update("survey_date", v)} disabled={payload.isLocked} />
              <Field label="Survey Reference No." value={form.survey_reference_no || ""} onChange={(v) => update("survey_reference_no", v)} disabled={payload.isLocked} placeholder="Reference number" />
              <Select label="Survey Type" value={form.survey_type || "Physical Survey"} options={[{ id: "Physical Survey", name: "Physical Survey" }, { id: "Self Survey", name: "Self Survey" }]} onChange={(v) => update("survey_type", v)} disabled={payload.isLocked} />
              <Select label="Survey Status" value={form.survey_status} options={[{ id: "Pending", name: "Pending" }, { id: "Completed", name: "Completed" }]} onChange={(v) => update("survey_status", v)} disabled={payload.isLocked} />
              <Field label="Survey Remarks" value={form.survey_remarks || ""} onChange={(v) => update("survey_remarks", v)} disabled={payload.isLocked} placeholder="Add survey remarks" />
            </div></section>
            <section className="claim-survey-panel claim-survey-documents"><h4>▣ Survey Documents</h4><div className="claim-survey-document-grid">{(payload.options?.documentSlots || []).slice(0, 3).map((slot) => { const selected = files[slot.inputName]?.length > 0; const saved = slot.documents?.length > 0; return <label key={slot.inputName} className={selected || saved ? "document-uploaded" : ""}><span>{slot.documentType}</span>{(selected || saved) && <i className="document-success">✓</i>}<input type="file" multiple onChange={(event) => setFiles((current) => ({ ...current, [slot.inputName]: Array.from(event.target.files || []) }))} disabled={payload.isLocked} />{selected ? <em>{files[slot.inputName][0].name}</em> : saved ? <em><a href={slot.documents[0].url} target="_blank" rel="noreferrer">View</a> · Replace</em> : <small>Choose PDF, JPG or PNG</small>}</label>})}</div></section>
            <section className="claim-survey-panel"><h4>▣ Survey Findings</h4><div className="claim-survey-fields">
              <Field label="Damage Type" value={form.damage_type || ""} onChange={(v) => update("damage_type", v)} disabled={payload.isLocked} placeholder="e.g. Rear bumper & tailgate" />
              <Field label="Estimated Repair Cost" type="number" value={form.estimated_amount || ""} onChange={(v) => update("estimated_amount", v)} disabled={payload.isLocked} placeholder="0" />
              <Select label="Salvage Applicable" value={form.salvage_applicable || "No"} options={[{ id: "Yes", name: "Yes" }, { id: "No", name: "No" }]} onChange={(v) => update("salvage_applicable", v)} disabled={payload.isLocked} />
              <Select label="Recommended Action" value={form.recommended_action || "Approve Repair"} options={[{ id: "Approve Repair", name: "Approve Repair" }, { id: "Re-inspection Required", name: "Re-inspection Required" }, { id: "Reject Claim", name: "Reject Claim" },{ id: "Required Documents", name: "Required Documents" },{ id: "Required KO", name: "Required KO Photos & 2nd Visit" },{ id: "Other", name: "Other As  per remarks" },{ id: "Assign Another", name: "Assign Another Surveyor" }]} onChange={(v) => update("recommended_action", v)} disabled={payload.isLocked} />
              <Field label="Additional Notes" value={form.survey_notes || ""} onChange={(v) => update("survey_notes", v)} disabled={payload.isLocked} placeholder="Add survey findings" />
            </div></section>
          </div>}</div>}
        {payload.currentStage >= 6 && <div className="claim-form-subsection"><button type="button" className="claim-form-subsection-heading" onClick={() => toggleSection("approval")}><span className="claim-form-subsection-icon approval">✓</span><span><h3>Insurance Approval</h3><p>Record approval confirmation and upload the assessment document.</p></span><b>{expandedSections.approval ? "⌃" : "⌄"}</b></button>{expandedSections.approval && <>{form.assessment_file && <button type="button" className="claim-assessment-open" onClick={openAssessment} disabled={!payload.jobcardId}>▣ Open Assessment Labour &amp; Parts</button>}
          
            <Field label="Insurance Approval Date" type="datetime-local" value={form.insurance_approval_date} onChange={(v) => update("insurance_approval_date", v)} disabled={payload.isLocked} />
            <Field label="Insurance Note" value={form.insurance_note} onChange={(v) => update("insurance_note", v)} disabled={payload.isLocked} />
            <div className="claim-document-upload-single"><label><span>Assessment Document</span><input type="file" onChange={(event) => setFiles((current) => ({ ...current, assessment_file: Array.from(event.target.files || []) }))} disabled={payload.isLocked} /></label>{form.assessment_file && <em>Existing: <a href={form.assessment_file} target="_blank" rel="noreferrer">View document</a><button type="button" className="claim-document-delete" onClick={deleteAssessmentFile} disabled={payload.isLocked} title="Delete uploaded document" aria-label="Delete uploaded document">🗑</button></em>}</div>
          </>}</div>}
        </div>

        </>
      )}
        <div className="claim-react-footer"><button type="button" onClick={() => window.location.href = "/claimList/"}>Cancel</button><button type="submit" disabled={saving || payload.isLocked}>{payload.isLocked ? "Claim Closed" : saving ? "Saving..." : "Save Claim"}</button>{!payload.isLocked && <button type="button" className="primary" onClick={(event) => submit(event, true)} disabled={saving}>{saving ? "Saving..." : "Save & Next →"}</button>}</div>
      </form>
      </div>
      <aside className="claim-react-sidebar">
        <section className="claim-snapshot claim-snapshot-modern">
          <div className="claim-snapshot-heading">
            <div className="claim-snapshot-icon">⌁</div>
            <div><h2>Vehicle &amp; Customer</h2><span>Linked claim information</span></div>
            {selectedVehicle && <span className="claim-linked-badge">Linked</span>}
          </div>
          {selectedVehicle ? <>
            <div className="claim-vehicle-preview"><div className="claim-vehicle-image-frame">{selectedVehicle.image ? <img src={selectedVehicle.image} alt={selectedVehicle.name} /> : <span>🚗</span>}
            </div>
              <div className="claim-vehicle-caption"><span>VEHICLE</span><strong>{selectedVehicle.name}</strong><small>Ready for claim processing</small>
              </div>
            </div>
            <div className="claim-sidebar-card-heading"><div className="claim-sidebar-card-icon">♢</div><div><h2>Insurance Information</h2><span>Policy information for this claim</span></div></div><div className="claim-insurance-company"><strong>{form.insurance_company_name || "Insurance Company"}</strong><small>Comprehensive Policy</small></div><div className="claim-insurance-meta"><div><span>Policy No.</span><strong>{form.policy_no || "-"}</strong></div><div><span>Valid Till</span><strong>{form.policy_end_date || "-"}</strong></div></div>{form.insurance_policy_document && <a className="claim-policy-link" href={form.insurance_policy_document} target="_blank" rel="noreferrer">▧ View Policy Document</a>}
            <div className="claim-customer-block">
              <div className="claim-customer-avatar">{(selectedVehicle.customer || "C").slice(0, 1).toUpperCase()}</div>
              <div><span>CUSTOMER</span><strong>{selectedVehicle.customer || "Not available"}</strong><small>Vehicle owner</small></div></div>
            <div className="claim-snapshot-selected">✓ Vehicle selected for this claim</div></> : <div className="claim-snapshot-empty"><div className="claim-empty-icon">🚘</div><strong>Vehicle not selected</strong><p>Select a vehicle to instantly view its customer and vehicle details.</p></div>}
        </section>
        {payload.isEdit && <section className="claim-stage-history-card"><div className="claim-stage-history-title">Stage Activity</div>{(payload.stageHistory || []).slice().reverse().map((item) => <div className="claim-stage-history-row" key={`${item.stage}-${item.changedAt}`}><span className="claim-history-check">✓</span><div><strong>{item.label}</strong><small>{item.changedAt} · {item.changedBy}</small></div></div>)}</section>}
        <section className="claim-snapshot-help"><div className="claim-help-icon">i</div><div><b>Quick tip</b><p>Confirm the registration and customer before saving the claim.</p></div></section>
      </aside>
  </div>
  {assessmentModalOpen && <div className="claim-assessment-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setAssessmentModalOpen(false)}><div className="claim-assessment-modal claim-assessment-modal-wide" role="dialog" aria-modal="true"><header className="claim-assessment-modal-header"><div><span>INSURANCE WORKFLOW</span><h2>Insurance Assessment</h2><small>Review parts and labour against the surveyor assessment.</small></div><button type="button" onClick={() => setAssessmentModalOpen(false)}>×</button></header>{assessmentError && <div className="claim-react-error">{assessmentError}</div>}{assessmentLoading ? <div className="claim-assessment-loading">Loading assessment...</div> : <><div className="claim-assessment-grid"><AssessmentTable title="Parts Assessment" rows={assessment.parts} type="part" onChange={(rows) => setAssessment((current) => ({ ...current, parts: rows }))} /><AssessmentTable title="Labour Assessment" rows={assessment.labours} type="labour" onChange={(rows) => setAssessment((current) => ({ ...current, labours: rows }))} /></div><div className="claim-assessment-actions"><button type="button" onClick={() => setAssessment((current) => ({ ...current, parts: [...current.parts, { is_new: true, part_no: "", description: "", amount: "0", revised_amount: "0", decision: "New" }] }))}>＋ Part</button><button type="button" onClick={() => setAssessment((current) => ({ ...current, labours: [...current.labours, { is_new: true, job_code: "", description: "", amount: "0", revised_amount: "0", decision: "Approved" }] }))}>＋ Labour</button></div><AssessmentApprovedRows parts={assessment.parts} labours={assessment.labours} /><footer><button type="button" onClick={() => window.print()}>Print Assessment</button><button type="button" className="primary" onClick={saveAssessment} disabled={assessmentSaving}>{assessmentSaving ? "Saving..." : "Save Assessment"}</button></footer></>}</div></div>}
  </main>;
}

function AssessmentTable({ title, rows, type, onChange, onDecision }) {
  const changeDecision = (index, decision) => {
    onChange(rows.map((item, i) => i === index ? { ...item, decision, revised_amount: decision === "New" ? (item.amount || "0") : "0" } : item));
  };
  return <section className="claim-assessment-modal-section"><div className="claim-assessment-modal-title"><b>{title}</b><span>{rows.length} entries</span></div><table><thead><tr><th>{type === "part" ? "Part" : "Job Code"}</th><th>Description</th><th>Amount</th><th>{type === "labour" ? "Paint Panel" : "Surveyor Assessment"}</th><th>Decision</th><th>Revised Amount</th></tr></thead><tbody>{rows.length ? rows.map((row, index) => <tr key={row.id || index}><td><input value={type === "part" ? row.part_no || "" : row.job_code || ""} onChange={(event) => onChange(rows.map((item, i) => i === index ? { ...item, [type === "part" ? "part_no" : "job_code"]: event.target.value } : item))} /></td><td><input value={row.description || ""} onChange={(event) => onChange(rows.map((item, i) => i === index ? { ...item, description: event.target.value } : item))} /></td><td>{row.amount || "0"}</td><td>{type === "labour" ? row.paint_panel_type || "-" : row.decision || "None"}</td><td><select className={type === "part" ? "part-decision" : "labour-decision"} value={row.decision || "None"} onChange={(event) => changeDecision(index, event.target.value)}><option>None</option><option>New</option><option>Repair</option><option>Approved</option><option>Rejected</option></select></td><td><input className={type === "part" ? "part-revised" : "labour-revised"} type="number" min="0" step="0.01" value={row.revised_amount ?? (row.amount || "0")} onChange={(event) => onChange(rows.map((item, i) => i === index ? { ...item, revised_amount: event.target.value } : item))} /></td></tr>) : <tr><td colSpan="6">No {title.toLowerCase()} entries found.</td></tr>}</tbody></table></section>;
}

function AssessmentApprovedRows({ parts, labours }) { const rows = [...parts.filter((item) => ["New", "Repair", "Approved"].includes(item.decision)).map((item) => ({ type: "Part", code: item.part_no, description: item.description, amount: item.amount, decision: item.decision, revised: item.revised_amount })), ...labours.filter((item) => ["New", "Repair", "Approved"].includes(item.decision)).map((item) => ({ type: "Labour", code: item.job_code, description: item.description, amount: item.amount, decision: item.decision, revised: item.revised_amount }))]; return <section className="claim-assessment-modal-section"><div className="claim-assessment-modal-title"><b>Surveyor Approved Entries</b><span>{rows.length} entries</span></div><table><thead><tr><th>Type</th><th>Code / Part No</th><th>Description</th><th>Original Amount</th><th>Surveyor Decision</th><th>Approved Amount</th></tr></thead><tbody>{rows.length ? rows.map((row, index) => <tr key={`${row.type}-${row.code}-${index}`}><td>{row.type}</td><td>{row.code || "-"}</td><td>{row.description || "-"}</td><td>{row.amount || "0"}</td><td>{row.decision}</td><td>{row.revised || "0"}</td></tr>) : <tr><td colSpan="6">No approved entries</td></tr>}</tbody></table></section>; }

function Field({ label, value, onChange, ...props }) { return <label className="claim-react-field"><span>{label}</span><input value={value || ""} onChange={(e) => onChange?.(e.target.value)} {...props} /></label>; }
function Select({ label, value, options = [], onChange, placeholder = "Select", disabled, searchable = false }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const selected = options.find((option) => String(option.id) === String(value));
  const filtered = useMemo(() => options.filter((option) => option.name.toLowerCase().includes(search.toLowerCase())), [options, search]);
  if (!searchable) return <label className="claim-react-field"><span>{label}</span><select value={value || ""} onChange={(e) => onChange(e.target.value)} disabled={disabled}><option value="">{placeholder}</option>{options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>;
  return <label className="claim-react-field"><span>{label}</span><div className="claim-tomselect"><div className="claim-tomselect-control" onClick={() => !disabled && setOpen(true)}><input value={open ? search : (selected?.name || "")} placeholder={placeholder} onChange={(e) => { setSearch(e.target.value); setOpen(true); }} disabled={disabled} /><b>⌄</b></div>{open && <div className="claim-tomselect-dropdown">{filtered.length ? filtered.map((option) => <button type="button" key={option.id} onClick={() => { onChange(String(option.id)); setSearch(""); setOpen(false); }}>{option.name}</button>) : <><em>No vehicles found</em><button type="button" className="claim-add-option" onClick={() => { window.location.href = "/vehicle/new/"; }}>＋ Add New Vehicle</button><button type="button" className="claim-add-option" onClick={() => { window.location.href = "/customer/new/"; }}>＋ Add New Customer</button></>}</div>}</div></label>;
}


function stageHistoryDescription(stage) {
  return {
    1: "Initial claim registration and basic details",
    2: "Claim assigned to service advisor",
    3: "Initial estimation and assessment",
    4: "Intimation sent to insurance company",
    5: "Survey completed and report received",
    6: "Claim approved by insurance company",
    7: "Job card created and work allocated",
  }[stage] || "Stage completed";
}

function CompletedStageDetails({ stage, form, payload, history }) {
  const value = (key, fallback = "-") => {
    const raw = form?.[key];
    return raw === undefined || raw === null || raw === "" ? fallback : raw;
  };
  const money = (rawValue) =>
    rawValue === undefined || rawValue === null || rawValue === ""
      ? "-"
      : `₹ ${Number(rawValue || 0).toLocaleString("en-IN", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`;

  const Detail = ({ label, children }) => (
    <div className="claim-history-detail">
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );

  const historyLine = history?.changedAt
    ? `${history.changedAt}${history.changedBy ? ` · ${history.changedBy}` : ""}`
    : "Completed";

  if (stage === 7) {
    const job = payload.jobcardWorkflow || {};
    return (
      <div className="claim-history-content claim-history-content-grid">
        <div className="claim-history-completed-banner">
          <span className="claim-history-detail-check">✓</span>
          <div>
            <strong>Work Allocation completed</strong>
            <small>{historyLine}</small>
          </div>
        </div>
        <div className="claim-history-detail-grid">
          <Detail label="Job Card">{job.jobNo || "Not created"}</Detail>
          <Detail label="Job Card Status">{job.repairStatus || "Open"}</Detail>
          <Detail label="Job Card Total">{money(job.grandTotal)}</Detail>
          <Detail label="Repair Progress">{job.hasRepairProgressStarted ? "Started" : "Not started"}</Detail>
        </div>
        {job.id && (
          <button
            type="button"
            className="claim-history-open-job"
            onClick={() => window.location.href = `/jobCard/${job.id}/edit/`}
          >
            Open Job Card →
          </button>
        )}
      </div>
    );
  }
  if (stage === 8) {
  const job = payload.jobcardWorkflow || {};

  return (
    <div className="claim-history-content claim-history-content-grid">
      <div className="claim-history-completed-banner">
        <span className="claim-history-detail-check">✓</span>
        <div>
          <strong>Repair Work completed</strong>
          <small>{historyLine}</small>
        </div>
      </div>

      <div className="claim-history-detail-grid">
        <Detail label="Job Card">
          {job.jobNo || "Not created"}
        </Detail>

        <Detail label="Job Card Status">
          {job.repairStatus || "Completed"}
        </Detail>
      </div>

      {job.id && (
        <button
          type="button"
          className="claim-history-open-job"
          onClick={() =>
            window.location.href = `/jobCard/${job.id}/edit/`
          }
        >
          Open Job Card →
        </button>
      )}
    </div>
  );
}

if (stage === 9) {
  const job = payload.jobcardWorkflow || {};

  return (
    <div className="claim-history-content claim-history-content-grid">
      <div className="claim-history-completed-banner">
        <span className="claim-history-detail-check">✓</span>
        <div>
          <strong>Work Completed</strong>
          <small>{historyLine}</small>
        </div>
      </div>

      <div className="claim-history-detail-grid">
        <Detail label="Job Card">
          {job.jobNo || "Not created"}
        </Detail>

        <Detail label="Job Card Status">
          {job.repairStatus || "Completed"}
        </Detail>
      </div>

      <div className="claim-history-action-row">
        {job.id && (
          <button
            type="button"
            className="claim-history-open-job"
            onClick={() =>
              window.location.href = `/jobCard/${job.id}/edit/`
            }
          >
            Open Job Card →
          </button>
        )}

        {job.id && (
          <button
            type="button"
            className="claim-history-open-job"
            onClick={() =>
              window.location.href =
                `/work-allocation/${job.id}/completion-report/`
            }
          >
            View Work Completion Report →
          </button>
        )}
      </div>
    </div>
  );
}
  const vehicleName =
    (payload.options?.vehicles || []).find(
      (item) => String(item.id) === String(form.vehicle)
    )?.name || value("vehicle");

  const advisorName =
    (payload.options?.employees || []).find(
      (item) => String(item.id) === String(form.employee)
    )?.name || value("employee");

  const detailMap = {
    1: [
      ["Claim No.", value("claim_no")],
      ["Claim Type", value("claim_type")],
      ["Created Date", value("claim_created_date")],
      ["Vehicle", vehicleName],
    ],
    2: [
      ["Advisor", advisorName],
      ["Claim No.", value("claim_no")],
    ],
    3: [
      ["Estimated Amount", money(value("estimated_amount", ""))],
      ["Claim No.", value("claim_no")],
      ["Vehicle", vehicleName],
    ],
    4: [
      ["Accident Date", value("accident_date")],
      ["Intimation Date", value("intimation_date")],
      ["Insurance Company", value("insurance_company_name")],
      ["Policy No.", value("policy_no")],
      ["Insurance Claim No.", value("ic_claim_no")],
    ],
    5: [
      ["Surveyor", value("surveyor")],
      ["Survey Date", value("survey_date")],
      ["Survey Status", value("survey_status")],
      ["Survey Reference", value("survey_reference_no")],
      ["Damage Type", value("damage_type")],
      ["Estimated Repair Cost", money(value("estimated_amount", ""))],
    ],
    6: [
      ["Approval Date", value("insurance_approval_date")],
      ["Insurance Company", value("insurance_company_name")],
      ["Approval Note", value("insurance_note")],
      ["Assessment Document", value("assessment_file", "Not uploaded")],
    ],
  };

  return (
    <div className="claim-history-content claim-history-content-grid">
      <div className="claim-history-completed-banner">
        <span className="claim-history-detail-check">✓</span>
        <div>
          <strong>Stage {stage} completed</strong>
          <small>{historyLine}</small>
        </div>
      </div>
      <div className="claim-history-detail-grid">
        {(detailMap[stage] || []).map(([label, detail]) => (
          <Detail key={label} label={label}>{detail}</Detail>
        ))}
      </div>

      {(stage === 4 || stage === 5 || stage === 6) && (
        <CompletedStageDocuments
          stage={stage}
          form={form}
          payload={payload}
        />
      )}
    </div>
  );
}

function CompletedStageDocuments({ stage, form, payload }) {
  const slots = payload.options?.documentSlots || [];

  const stageSlots =
    stage === 4
      ? slots
      : stage === 5
        ? slots.slice(0, 3)
        : [];

  const uploadedSlots = stageSlots.filter(
    (slot) => slot.documents?.some((document) => document.url)
  );

  if (stage === 6) {
    if (!form.assessment_file) {
      return (
        <div className="claim-history-documents">
          <div className="claim-history-documents-heading">
            <span>DOCUMENTS</span>
            <strong>Assessment Document</strong>
          </div>
          <div className="claim-history-no-document">
            No assessment document uploaded.
          </div>
        </div>
      );
    }

    return (
      <div className="claim-history-documents">
        <div className="claim-history-documents-heading">
          <span>DOCUMENTS</span>
          <strong>Assessment Document</strong>
        </div>
        <div className="claim-history-document-list">
          <div className="claim-history-document-row">
            <div>
              <span className="claim-history-document-icon">▧</span>
              <div>
                <strong>Assessment Document</strong>
                <small>Uploaded during Insurance Approval</small>
              </div>
            </div>
            <a
              href={form.assessment_file}
              target="_blank"
              rel="noreferrer"
              className="claim-history-document-view"
            >
              View
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="claim-history-documents">
      <div className="claim-history-documents-heading">
        <span>DOCUMENTS</span>
        <strong>
          {stage === 4 ? "Claim Intimation Documents" : "Survey Documents"}
        </strong>
      </div>

      {uploadedSlots.length ? (
        <div className="claim-history-document-list">
          {uploadedSlots.map((slot) =>
            slot.documents
              .filter((document) => document.url)
              .map((document, index) => (
                <div
                  className="claim-history-document-row"
                  key={`${slot.inputName}-${index}`}
                >
                  <div>
                    <span className="claim-history-document-icon">▧</span>
                    <div>
                      <strong>{slot.documentType}</strong>
                      <small>Document uploaded</small>
                    </div>
                  </div>

                  <a
                    href={document.url}
                    target="_blank"
                    rel="noreferrer"
                    className="claim-history-document-view"
                  >
                    View
                  </a>
                </div>
              ))
          )}
        </div>
      ) : (
        <div className="claim-history-no-document">
          No documents uploaded for this stage.
        </div>
      )}
    </div>
  );
}

function StageWorkspace({ stage, payload, form, update, setFiles, disabled }) {
  const job = payload.jobcardWorkflow || {};
  const claim = payload.claimWorkflow || {};
  const meta = {
    7:["Work Allocation","The linked Job Card is ready for workshop allocation and execution."],
    8:["Repair Work","Repair progress is controlled from Work Allocation and the linked Job Card."],
    9:["Work Completed","Confirm the workshop has completed the approved repair work."],
    10:["Re Inspection","Record the final inspection result and evidence before liability."],
    11:["Liability","Record the liability / DO information received from the insurer."],
    12:["Invoiced","Record the final invoice and payment details after the Job Card is closed."],
    13:["Delivery","Capture the actual handover details before closing the claim."],
    14:["Claim Closed","This claim has completed the 14-stage workflow."]
  }[stage];
  if (!meta) return null;
  const status=(value,label="Complete")=>value?<span className="claim-workflow-status done">✓ {label}</span>:<span className="claim-workflow-status pending">Pending</span>;
  const money=(value)=>`₹ ${Number(value||0).toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2})}`;
  const field=(label,key,type="text",extra={})=><Field label={label} type={type} value={form[key]??""} onChange={(v)=>update(key,v)} disabled={disabled} {...extra}/>;
  return <section className="claim-stage-workspace">
    {/* CURRENT STAGE HEADER */}
  <div className="claim-stage-workspace-head">
    <div>
      <span>STAGE {stage}</span>
      <h3>{meta[0]}</h3>
      <p>{meta[1]}</p>
    </div>

    <span className={`claim-workflow-status ${stage === 14 ? "done" : "info"}`}>
      {stage === 14 ? "✓ Completed" : "Active"}
    </span>
  </div>
  {/* STAGE 7 & 8 — SIMPLE JOB CARD */}
  {(stage === 7 || stage === 8) && (
    <div className="claim-simple-jobcard">
      <div className="claim-simple-jobcard-info">
        <span>LINKED JOB CARD</span>
        <strong>{job.jobNo || "Not created"}</strong>
      </div>

      {job.id && (
        <button
          type="button"
          className="claim-simple-jobcard-open"
          onClick={() =>
            window.location.href = `/jobCard/${job.id}/edit/`
          }
        >
          Open Job Card →
        </button>
      )}
    </div>
  )}


  {/* STAGE 8 COMPLETED — WORK COMPLETION REPORT */}
  {stage === 9 && (
    <div className="claim-work-completion-report">

      <div className="claim-work-completion-report-info">
        <span>STAGE 8 — WORK COMPLETED</span>

        <strong>Work Completion Report</strong>

        <p>
          Stage 8 has been completed. View the work completion report.
        </p>
      </div>

      <button
        type="button"
        className="claim-work-completion-report-btn"
        onClick={() =>
  window.location.href = `/work-allocation/${job.id}/completion-report/`
}
      >
        View Work Completion Report →
      </button>

    </div>
  )}

    {stage===10&&<div className="claim-workflow-section"><div className="claim-workflow-section-head"><div><span>FINAL INSPECTION</span><h4>Re Inspection</h4></div><span className={`claim-workflow-status ${form.reinspection_done?"done":"pending"}`}>{form.reinspection_done?"Completed":"Pending"}</span></div><div className="claim-workflow-fields"><label className="claim-react-field claim-workflow-checkbox"><span>Re Inspection Completed</span><label><input type="checkbox" checked={Boolean(form.reinspection_done)} onChange={(e)=>update("reinspection_done",e.target.checked)} disabled={disabled}/> <b>Final inspection completed</b></label></label>{field("Re Inspection Date","reinspection_date","datetime-local")}{field("Re Inspection Done By","reinspection_done_by","text",{placeholder:"Inspector / employee name"})}</div><div className="claim-reinspection-upload"><div><span>RE INSPECTION EVIDENCE</span><strong>{payload.reinspectionPhotoCount||0} saved photos</strong></div><label className="claim-file-picker"><input type="file" accept="image/*" multiple onChange={(e)=>setFiles((current)=>({...current,reinspection_images:Array.from(e.target.files||[])}))} disabled={disabled}/><b>＋ Add re-inspection photos</b><small>Photos are submitted with Save Claim / Next.</small></label></div></div>}
    {stage===11&&<div className="claim-workflow-section"><div className="claim-workflow-section-head"><div><span>LIABILITY / DO</span><h4>Liability Receipt</h4></div><span className="claim-workflow-status info">Insurance settlement input</span></div><div className="claim-workflow-fields">{field("Liability Received Date","liability_received_at","datetime-local")}{field("Liability / DO Amount","liability_do_amount","number",{min:"0",step:"0.01"})}{field("Customer Payable","deductible","number",{min:"0",step:"0.01"})}</div>{claim.liabilityDocumentUrl&&<a className="claim-workflow-document" href={claim.liabilityDocumentUrl} target="_blank" rel="noreferrer">View existing liability document</a>}</div>}
    {stage===12&&<div className="claim-workflow-section"><div className="claim-workflow-section-head"><div><span>FINAL BILLING</span><h4>Invoice & Payment</h4></div><span className={`claim-workflow-status ${job.repairStatus==="Closed"?"done":"pending"}`}>{job.repairStatus==="Closed"?"Job Card Closed":"Close Job Card First"}</span></div><div className="claim-workflow-financials"><div><small>Parts</small><strong>{money(job.partsTotal)}</strong></div><div><small>Labour</small><strong>{money(job.labourTotal)}</strong></div><div><small>Job Card Total</small><strong>{money(job.grandTotal)}</strong></div><div><small>Approved</small><strong>{money(claim.approvedAmount)}</strong></div></div><div className="claim-workflow-fields">{field("Invoice Date","invoice_datetime","datetime-local")}{field("Invoice Amount","invoice_amount","number",{min:"0",step:"0.01"})}{field("Invoice Parts Amount","invoice_parts_amount","number",{min:"0",step:"0.01"})}{field("Invoice Labour Amount","invoice_labour_amount","number",{min:"0",step:"0.01"})}<Select label="Payment Mode" value={form.payment_mode||""} options={(payload.paymentModes||[]).map((x)=>({id:x.value,name:x.label}))} onChange={(v)=>update("payment_mode",v)} disabled={disabled}/>{field("Payment Details","payment_details","text",{placeholder:"Reference / transaction details"})}</div></div>}
    {stage===13&&<div className="claim-workflow-section"><div className="claim-workflow-section-head"><div><span>CUSTOMER HANDOVER</span><h4>Delivery Details</h4></div><span className="claim-workflow-status info">Final handover</span></div><div className="claim-workflow-fields">{field("Delivery Date & Time","delivery_datetime","datetime-local")}<Select label="Delivered To" value={form.delivered_to||""} options={[{id:"Customer Self",name:"Customer Self"},{id:"Customer Representative",name:"Customer Representative"},{id:"Drop By Driver",name:"Drop By Driver"}]} onChange={(v)=>update("delivered_to",v)} disabled={disabled}/>{field("Driver / Representative Name","delivery_driver_name","text",{placeholder:"Name if applicable"})}{field("Delivery Remarks","delivery_remarks","text",{placeholder:"Handover remarks"})}</div><div className="claim-delivery-gates"><div>{status(job.roadTestDone)}<span>Road Test</span></div><div>{status(job.washingDone)}<span>Washing</span></div><div>{status(job.readyForDelivery)}<span>Ready for Delivery</span></div></div></div>}
    {stage===14&&<div className="claim-closed-summary"><div className="claim-closed-icon">✓</div><div><strong>Claim workflow completed</strong><p>Claim {claim.claimNo||""} is at Closed stage. Normal users cannot edit a closed claim.</p></div></div>}
  </section>;
}
