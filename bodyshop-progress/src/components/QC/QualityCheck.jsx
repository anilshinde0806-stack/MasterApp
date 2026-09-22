import React, { useEffect, useMemo, useRef, useState } from "react";
import "./QualityCheck.css";

const CATEGORY_META = {
  Exterior: { number: 1, icon: "🚗" },
  "Paint & Body": { number: 2, icon: "🎨" },
  Interior: { number: 3, icon: "💺" },
  Electrical: { number: 4, icon: "⚡" },
  Mechanical: { number: 5, icon: "🔧" },
  Safety: { number: 6, icon: "🛡️" },
  "Road Test": { number: 7, icon: "◉" },
  "Documents & Accessories": { number: 8, icon: "📄" },
};

const STATUS = {
  OK: { label: "Pass", short: "✓", className: "qc-pass" },
  ATTENTION: { label: "Attention", short: "!", className: "qc-attention" },
  NOT_OK: { label: "Fail", short: "×", className: "qc-fail" },
  NA: { label: "N/A", short: "×", className: "qc-na" },
  PENDING: { label: "Pending", short: "•", className: "qc-pending" },
};

function csrfToken() {
  const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function normalizeStatus(status) {
  const value = String(status || "PENDING").toUpperCase();
  if (value === "NOT OK") return "NOT_OK";
  return STATUS[value] ? value : "PENDING";
}

function normalizePayload(raw) {
  const qc = raw?.quality_check || raw || {};
  return {
    ...raw,
    quality_check: {
      ...qc,
      items: Array.isArray(qc.items) ? qc.items : [],
      evidence_photos: Array.isArray(qc.evidence_photos)
        ? qc.evidence_photos
        : [],
    },
  };
}

function groupItems(items) {
  const groups = {};
  items.forEach((raw) => {
    const item = {
      ...raw,
      status: normalizeStatus(raw.status),
    };
    const category = item.category || "Other";
    if (!groups[category]) {
      groups[category] = {
        title: category,
        number: item.category_order || CATEGORY_META[category]?.number || 99,
        icon: CATEGORY_META[category]?.icon || "✓",
        checks: [],
      };
    }
    groups[category].checks.push(item);
  });

  return Object.values(groups)
    .sort((a, b) => a.number - b.number)
    .map((group) => ({
      ...group,
      checks: group.checks.sort(
        (a, b) => (a.item_order || 0) - (b.item_order || 0)
      ),
    }));
}

function Progress({ value }) {
  return (
    <div className="qc-progress">
      <div className="qc-progress-fill" style={{ width: `${value}%` }} />
    </div>
  );
}

function StatusPill({ status }) {
  const meta = STATUS[status] || STATUS.PENDING;
  return (
    <span className={`qc-status-pill ${meta.className}`}>
      {meta.label}
    </span>
  );
}

function Donut({ total, pass, attention, fail, na }) {
  const checked = pass + attention + fail + na;
  const passPct = total ? (pass / total) * 100 : 0;
  const attentionPct = total ? (attention / total) * 100 : 0;
  const failPct = total ? (fail / total) * 100 : 0;

  const style = {
    background: `conic-gradient(
      #13b978 0 ${passPct}%,
      #f59e0b ${passPct}% ${passPct + attentionPct}%,
      #ef4444 ${passPct + attentionPct}% ${passPct + attentionPct + failPct}%,
      #cbd5e1 ${passPct + attentionPct + failPct}% 100%
    )`,
  };

  return (
    <div className="qc-donut-wrap">
      <div className="qc-donut" style={style}>
        <div className="qc-donut-inner">
          <strong>{total}</strong>
          <span>Total Checks</span>
        </div>
      </div>
      <div className="qc-legend">
        <div><i className="legend-pass" /> Pass <b>{pass}</b></div>
        <div><i className="legend-attention" /> Attention <b>{attention}</b></div>
        <div><i className="legend-fail" /> Fail <b>{fail}</b></div>
        <div><i className="legend-na" /> N/A <b>{na}</b></div>
        {checked < total && <small>{total - checked} pending</small>}
      </div>
    </div>
  );
}

export default function QualityCheck({ jobId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [remarks, setRemarks] = useState("");
  const [remarkItem, setRemarkItem] = useState(null);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [message, setMessage] = useState("");

  const photoInputRef = useRef(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `/jobCard/${jobId}/quality-check/?format=json`,
        {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        }
      );
      const payload = await response.json();
      if (!response.ok) throw new Error(payload?.message || "Unable to load Quality Check.");
      setData(normalizePayload(payload));
    } catch (err) {
      setError(err.message || "Unable to load Quality Check.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [jobId]);

  const qc = data?.quality_check || {};
  const items = qc.items || [];
  const categories = useMemo(() => groupItems(items), [items]);

  const counts = useMemo(() => {
    const result = { OK: 0, ATTENTION: 0, NOT_OK: 0, NA: 0, PENDING: 0 };
    items.forEach((item) => {
      result[normalizeStatus(item.status)] += 1;
    });
    return result;
  }, [items]);

  const total = items.length;
  const checked = total - counts.PENDING;
  const overallProgress = total ? Math.round((checked / total) * 100) : 0;

  async function postAction(formData) {
    const response = await fetch(`/jobCard/${jobId}/quality-check/`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.status === "error") {
      throw new Error(payload?.message || "Unable to save Quality Check.");
    }

    return payload;
  }

  async function updateItem(item, status, itemRemarks = item.remarks || "") {
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const fd = new FormData();
      fd.append("action", "update_item");
      fd.append("item_id", item.id);
      fd.append("status", status);
      fd.append("remarks", itemRemarks);

      await postAction(fd);

      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          quality_check: {
            ...current.quality_check,
            items: current.quality_check.items.map((row) =>
              row.id === item.id
                ? { ...row, status, remarks: itemRemarks }
                : row
            ),
          },
        };
      });

      setMessage("Checklist item saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function chooseStatus(item, status) {
    // First click on an unprocessed item = Pass + auto-save.
    if (status === "OK") {
      updateItem(item, "OK", "");
      return;
    }

    // Attention / Fail require remarks.
    if (status === "ATTENTION" || status === "NOT_OK") {
      setRemarkItem({ ...item, pendingStatus: status });
      setRemarks(item.remarks || "");
      return;
    }

    // N/A can be saved directly.
    updateItem(item, "NA", item.remarks || "");
  }

  // Left side of a checklist row = Pass.
  // Right side = Attention / Fail, which opens the remarks popup.
  function handlePassClick(item) {
    const status = normalizeStatus(item.status);

    if (status === "OK") {
      // Already Pass: clicking again opens remarks editor.
      setRemarkItem({ ...item, pendingStatus: "OK" });
      setRemarks(item.remarks || "");
      return;
    }

    updateItem(item, "OK", "");
  }

  function handleIssueClick(item) {
    const status = normalizeStatus(item.status);

    // If already an issue, edit its remarks.
    if (status === "ATTENTION" || status === "NOT_OK") {
      setRemarkItem({ ...item, pendingStatus: status });
      setRemarks(item.remarks || "");
      return;
    }

    // New issue: default to Attention.
    setRemarkItem({ ...item, pendingStatus: "ATTENTION" });
    setRemarks(item.remarks || "");
  }

  function handleStatusIconClick(item) {
    const status = normalizeStatus(item.status);

    if (status === "PENDING") {
      handlePassClick(item);
    } else if (status === "OK") {
      handlePassClick(item);
    } else {
      handleIssueClick(item);
    }
  }

  function openRemarkEditor(item) {
    const status = normalizeStatus(item.status);

    setRemarkItem({
      ...item,
      pendingStatus: status === "PENDING" ? "OK" : status,
    });

    setRemarks(item.remarks || "");
  }

  async function saveRemark() {
    if (!remarkItem) return;

    const status = normalizeStatus(remarkItem.pendingStatus);

    // Remarks are required when saving an issue.
    if (
      (status === "ATTENTION" || status === "NOT_OK") &&
      !remarks.trim()
    ) {
      setError("Please enter remarks for Attention / Fail.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");

    try {
      await updateItem(
        remarkItem,
        status === "PENDING" ? "OK" : status,
        remarks.trim()
      );

      setRemarkItem(null);
      setRemarks("");
    } catch (err) {
      setError(err.message || "Unable to save remarks.");
    } finally {
      setSaving(false);
    }
  }



  async function uploadPhoto(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setPhotoUploading(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("action", "upload_photos");
      fd.append("photos", file);

      await postAction(fd);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setPhotoUploading(false);
    }
  }

  async function deletePhoto(photoId) {
    try {
      const fd = new FormData();
      fd.append("action", "delete_photo");
      fd.append("photo_id", photoId);
      await postAction(fd);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) {
    return <div className="qc-loading">Loading Quality Inspection Checklist…</div>;
  }

  if (error && !data) {
    return <div className="qc-error">{error}</div>;
  }

  const vehicle = data?.vehicle || qc.vehicle || {};
  const job = data?.jobcard || qc.jobcard || {};
  const customer = data?.customer || qc.customer || {};
  const photos = qc.evidence_photos || [];

  return (
    <div className="quality-page">
      <header className="qc-header">
        <div>
          <h1>Quality Inspection Checklist</h1>
        </div>

        <label className="qc-date">
          <span>Inspection Date:</span>
          <input
            type="date"
            value={qc.inspection_date || ""}
            readOnly
          />
        </label>
      </header>

      {error && <div className="qc-alert">{error}</div>}
      {message && <div className="qc-success">{message}</div>}

      <div className="qc-layout">
        <main className="qc-main">
          <div className="qc-category-grid">
            {categories.map((category) => {
              const categoryChecked = category.checks.filter(
                (item) => item.status !== "PENDING"
              ).length;
              const categoryProgress = category.checks.length
                ? Math.round((categoryChecked / category.checks.length) * 100)
                : 0;

              return (
                <section className="qc-card" key={category.title}>
                  <div className="qc-card-heading">
                    <div className="qc-category-title">
                      <span className="qc-category-icon">{category.icon}</span>
                      <strong>
                        {category.number}. {category.title}
                      </strong>
                    </div>
                    <span className="qc-count">
                      {categoryChecked} / {category.checks.length}
                    </span>
                  </div>

                  <Progress value={categoryProgress} />

                  <div className="qc-check-list">
                    {category.checks.map((item) => {
                      const status = normalizeStatus(item.status);
                      const meta = STATUS[status] || STATUS.PENDING;

                      return (
                        <div className="qc-check-row" key={item.id}>
                          <button
                            type="button"
                            className={`qc-check-icon qc-left-action ${
                              status === "OK" ? "qc-pass" : "qc-pending"
                            }`}
                            title={
                              status === "OK"
                                ? `Edit remarks for ${item.item_name}`
                                : `Mark ${item.item_name} as Pass`
                            }
                            disabled={saving}
                            onClick={() => handlePassClick(item)}
                          >
                            {status === "OK" ? "✓" : "○"}
                          </button>

                          <div className="qc-item-name">
                            <span>{item.item_name}</span>
                            {item.remarks && (
                              <button
                                type="button"
                                className="qc-remark-link"
                                onClick={() => openRemarkEditor(item)}
                              >
                                View remarks
                              </button>
                            )}
                          </div>

                          <button
                            type="button"
                            className={`qc-status-button qc-right-action ${
                              status === "ATTENTION"
                                ? "qc-attention"
                                : status === "NOT_OK"
                                  ? "qc-fail"
                                  : "qc-issue-empty"
                            }`}
                            disabled={saving}
                            onClick={() => handleIssueClick(item)}
                          >
                            {status === "ATTENTION"
                              ? "Attention"
                              : status === "NOT_OK"
                                ? "Fail"
                                : "Attention / Fail"}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </section>
              );
            })}

            <section className="qc-card qc-result-card">
              <h3>QC Result</h3>

              <div className="qc-result-buttons">
                <button
                  type="button"
                  className={`qc-result-pass ${qc.result === "OK" ? "selected" : ""}`}
                  disabled={saving}
                >
                  ✓ PASS
                </button>

                <button
                  type="button"
                  className={`qc-result-fail ${qc.result === "NOT_OK" ? "selected" : ""}`}
                  disabled={saving}
                >
                  × FAIL
                </button>
              </div>

              <h4>Remarks</h4>
              <div className="qc-overall-remarks">
                {qc.remarks || "No overall remarks recorded."}
              </div>

              <h4>Photos / Attachments</h4>
              <div className="qc-photos">
                {photos.map((photo) => (
                  <div className="qc-photo" key={photo.id}>
                    <img src={photo.url} alt="QC evidence" />
                    <button
                      type="button"
                      onClick={() => deletePhoto(photo.id)}
                      title="Delete photo"
                    >
                      ×
                    </button>
                  </div>
                ))}

                <button
                  type="button"
                  className="qc-add-photo"
                  disabled={photoUploading}
                  onClick={() => photoInputRef.current?.click()}
                >
                  <span>▧</span>
                  {photoUploading ? "Uploading…" : "Add Photo"}
                </button>

                <input
                  ref={photoInputRef}
                  type="file"
                  accept="image/*"
                  hidden
                  onChange={uploadPhoto}
                />
              </div>
            </section>
          </div>
        </main>

        <aside className="qc-sidebar">
          <section className="qc-side-card">
            <h3>Quick Info</h3>
            <Info label="Make / Model" value={vehicle.make_model || vehicle.make || "—"} />
            <Info label="Reg. No." value={vehicle.registration_no || vehicle.reg_no || "—"} />
            <Info label="Customer" value={customer.name || "—"} />
            <hr />
            <Info label="Job Card No." value={job.job_no || "—"} />
            <Info label="Claim No." value={job.claim_no || "—"} />
            <Info label="Advisor" value={job.advisor_name || "—"} />
            <Info label="Insurance" value={job.insurance || "—"} />
          </section>

          <section className="qc-side-card">
            <h3>Inspection Summary</h3>
            <Donut
              total={total}
              pass={counts.OK}
              attention={counts.ATTENTION}
              fail={counts.NOT_OK}
              na={counts.NA}
            />
          </section>

          <div className="qc-side-progress">
            <strong>{overallProgress}%</strong>
            <span>Inspection complete</span>
          </div>
        </aside>
      </div>

      <footer className="qc-footer">
        <button type="button" className="qc-secondary" onClick={load}>
          ↻ Reset
        </button>

        <button type="button" className="qc-secondary" onClick={load}>
          ↻ Refresh
        </button>

        <button
          type="button"
          className="qc-complete"
          onClick={() => setMessage("QC completion action is ready for your backend endpoint.")}
        >
          ✓ Mark QC Completed
        </button>
      </footer>

      {remarkItem && (
        <div className="qc-modal-backdrop" onMouseDown={() => setRemarkItem(null)}>
          <div
            className="qc-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="qc-modal-close"
              onClick={() => setRemarkItem(null)}
            >
              ×
            </button>

            <h2>{remarkItem.pendingStatus === "OK" ? "Add Remarks" : "Add Remarks"}</h2>

            <p>
              <strong>Item:</strong> {remarkItem.item_name}
            </p>

            <p className="qc-modal-status">
              <strong>Status:</strong>{" "}
              <StatusPill status={remarkItem.pendingStatus} />
            </p>

            <textarea
              autoFocus
              maxLength={500}
              value={remarks}
              onChange={(event) => setRemarks(event.target.value)}
              placeholder="Enter remarks here..."
            />

            <div className="qc-character-count">
              {remarks.length}/500
            </div>

            <div className="qc-modal-actions">
              <button
                type="button"
                className="qc-secondary"
                onClick={() => setRemarkItem(null)}
              >
                Cancel
              </button>

              <button
                type="button"
                className="qc-complete"
                onClick={saveRemark}
                disabled={saving || !remarks.trim()}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="qc-info">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}
