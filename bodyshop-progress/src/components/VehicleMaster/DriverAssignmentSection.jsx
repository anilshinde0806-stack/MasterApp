import React, { useEffect, useRef, useState } from "react";
import TomSelect from "tom-select";
import "tom-select/dist/css/tom-select.css";
import "./DriverAssignmentSection.css";


export default function DriverAssignmentSection({ vehicle, drivers = [], assignedDriverIds = null, onAssignDriver, onUnassignDriver, onOpenDriverMaster }) {
  const hasControlledAssignments = Array.isArray(assignedDriverIds);
  const assignedIds = new Set((assignedDriverIds || []).map(String));
  const assignedDrivers = hasControlledAssignments
    ? drivers.filter((driver) => assignedIds.has(String(driver.id)))
    : drivers.filter((driver) => String(driver.vehicle_id) === String(vehicle?.id));
  const [selectedId, setSelectedId] = useState(null);
  const [detailsVisible, setDetailsVisible] = useState(false);
  const selectRef = useRef(null);
  const tomSelectRef = useRef(null);
  const [driverDropdownOpen, setDriverDropdownOpen] =
  useState(false);

const [driverSearch, setDriverSearch] =
  useState("");

const [selectedDriverIds, setSelectedDriverIds] =
  useState([]);
  useEffect(() => {
    if (!selectRef.current) return undefined;
    tomSelectRef.current?.destroy();
    tomSelectRef.current = new TomSelect(selectRef.current, {
      placeholder: "Search driver by name...",
      allowEmptyOption: true,
      maxItems: 1,
      create: false,
      sortField: { field: "text", direction: "asc" },
    });
    return () => tomSelectRef.current?.destroy();
  }, [drivers.length, assignedDrivers.length]);

  const assignSelectedDriver = () => {
    const driverId = tomSelectRef.current?.getValue();
    if (!driverId || !onAssignDriver) return;
    onAssignDriver(driverId);
    tomSelectRef.current.clear(true);
  };

  useEffect(() => {
    if (!assignedDrivers.some((driver) => String(driver.id) === String(selectedId))) {
      setSelectedId(assignedDrivers[0]?.id ?? null);
    }
  }, [vehicle?.id, assignedDrivers.length, selectedId]);

  const selectedDriver = assignedDrivers.find((driver) => String(driver.id) === String(selectedId)) || assignedDrivers[0];

  return (
    <section className="driver-assignment-section">
      <div className="driver-assignment-card">
        <div className="driver-assignment-card-header">
          <div className="driver-section-icon">👤</div>
          <div><h3>Assign / Change Driver</h3><p>Manage the drivers assigned to this vehicle.</p></div>
        </div>
        <div className="driver-assignment-card-body">
          <div className="assignment-vehicle-info">
            <div className="assignment-car-icon">🚗</div>
            <div><strong>{vehicle?.registration_no || "—"}</strong><span>{vehicle?.model_name || "Vehicle"}</span><small>Customer: {vehicle?.customer_name || "—"}</small></div>
          </div>
          <div className="assignment-divider" />
          <div className="assignment-action-area">
            <label className="driver-select-label" htmlFor="driver-assignment-select">Select Driver</label>
            <div className="driver-multi-select">
  <div className="driver-select-label">
    <span>Assign Driver</span>

    {selectedDriverIds.length > 0 && (
      <span className="driver-selected-count">
        {selectedDriverIds.length} Selected
      </span>
    )}
  </div>

  <div
    className={`driver-select-box ${
      driverDropdownOpen ? "active" : ""
    }`}
    onClick={() =>
      setDriverDropdownOpen((previous) => !previous)
    }
  >
    <div className="driver-selected-items">
      {selectedDriverIds.length === 0 ? (
        <div className="driver-select-placeholder">
          <i className="ri-user-search-line" />
          <span>Search driver...</span>
        </div>
      ) : (
        selectedDriverIds.map((driverId) => {
          const driver = drivers.find(
            (item) =>
              String(item.id) === String(driverId)
          );

          if (!driver) return null;

          return (
            <div
              className="driver-chip"
              key={driver.id}
            >
              <div className="driver-chip-avatar">
                {driver.face_photo ? (
                  <img
                    src={driver.face_photo}
                    alt=""
                  />
                ) : (
                  <i className="ri-user-line" />
                )}
              </div>

              <span>
                {driver.name}
              </span>

              <button
                type="button"
                className="driver-chip-remove"
                onClick={(event) => {
                  event.stopPropagation();

                  setSelectedDriverIds((previous) =>
                    previous.filter(
                      (id) =>
                        String(id) !==
                        String(driver.id)
                    )
                  );
                }}
              >
                <i className="ri-close-line" />
              </button>
            </div>
          );
        })
      )}
    </div>

    <button
      type="button"
      className="driver-toggle-btn"
      onClick={(event) => {
        event.stopPropagation();

        setDriverDropdownOpen(
          (previous) => !previous
        );
      }}
    >
      <i className="ri-arrow-down-s-line" />
    </button>
  </div>

  {driverDropdownOpen && (
    <div
      className="driver-dropdown"
      onClick={(event) =>
        event.stopPropagation()
      }
    >
      <div className="driver-search-box">
        <i className="ri-search-line" />

        <input
          type="text"
          value={driverSearch}
          onChange={(event) =>
            setDriverSearch(event.target.value)
          }
          placeholder="Search driver..."
          autoFocus
        />
      </div>

      <div className="driver-options">
        {drivers
          .filter(
            (driver) =>
              !assignedIds.has(
                String(driver.id)
              )
          )
          .filter((driver) => {
            const search =
              driverSearch
                .toLowerCase()
                .trim();

            if (!search) return true;

            return (
              driver.name
                ?.toLowerCase()
                .includes(search) ||
              driver.mobile_no
                ?.toLowerCase()
                .includes(search) ||
              driver.driving_license_no
                ?.toLowerCase()
                .includes(search)
            );
          })
          .map((driver) => {
            const selected =
              selectedDriverIds.some(
                (id) =>
                  String(id) ===
                  String(driver.id)
              );

            return (
              <button
                type="button"
                key={driver.id}
                className={`driver-option ${
                  selected ? "selected" : ""
                }`}
                onClick={() => {
                  setSelectedDriverIds(
                    (previous) => {
                      if (
                        previous.some(
                          (id) =>
                            String(id) ===
                            String(driver.id)
                        )
                      ) {
                        return previous.filter(
                          (id) =>
                            String(id) !==
                            String(driver.id)
                        );
                      }

                      return [
                        ...previous,
                        String(driver.id),
                      ];
                    }
                  );
                }}
              >
                <div className="driver-option-left">

                  <div className="driver-option-avatar">
                    {driver.face_photo ? (
                      <img
                        src={driver.face_photo}
                        alt=""
                      />
                    ) : (
                      <i className="ri-user-line" />
                    )}
                  </div>

                  <div className="driver-option-info">
                    <strong>
                      {driver.name}
                    </strong>

                    <span>
                      {driver.mobile_no ||
                        "No mobile number"}
                    </span>
                  </div>

                </div>

                <div className="driver-option-right">
                  {selected && (
                    <i className="ri-check-line" />
                  )}
                </div>
              </button>
            );
          })}

        {drivers.filter(
          (driver) =>
            !assignedIds.has(
              String(driver.id)
            )
        ).length === 0 && (
          <div className="driver-empty">
            <i className="ri-user-search-line" />

            <strong>
              No drivers available
            </strong>

            <span>
              All available drivers are already
              assigned.
            </span>
          </div>
        )}
      </div>

      <div className="driver-dropdown-footer">
        <button
          type="button"
          className="driver-clear-btn"
          onClick={() => {
            setSelectedDriverIds([]);
            setDriverSearch("");
          }}
        >
          <i className="ri-delete-bin-6-line" />
          Clear
        </button>

        <button
          type="button"
          className="driver-apply-btn"
          onClick={() => {
            setDriverDropdownOpen(false);
            setDriverSearch("");
          }}
        >
          <i className="ri-check-line" />
          Apply
        </button>
      </div>
    </div>
  )}
</div>
            <span className="assignment-label">Currently Assigned</span>
            <strong className={selectedDriver ? "" : "not-assigned-text"}>{selectedDriver?.name || "No Driver Assigned"}</strong>
            <button type="button" className="driver-blue-button" onClick={assignSelectedDriver}>
              Assign Driver
            </button>
          </div>
        </div>
      </div>

      <div className="driver-details-card" onMouseLeave={() => setDetailsVisible(false)}>
        <div className="driver-details-card-header">
          <div><h3>Driver Details</h3><p>Information for the selected driver.</p></div>
          {assignedDrivers.length > 1 && <span className="driver-selection-hint">Hover a driver to expand details</span>}
        </div>
        {assignedDrivers.length > 0 && <div className="assigned-driver-list right-driver-list">
          {assignedDrivers.map((driver) => (
            <button
              type="button"
              key={driver.id}
              className={`assigned-driver-item ${String(driver.id) === String(selectedDriver?.id) ? "active" : ""}`}
              onMouseEnter={() => { setSelectedId(driver.id); setDetailsVisible(true); }}
              onFocus={() => { setSelectedId(driver.id); setDetailsVisible(true); }}
              onClick={() => { setSelectedId(driver.id); setDetailsVisible(true); }}
            >
              {driver.photo ? <img src={driver.photo} alt="" /> : <span className="assigned-driver-avatar">👤</span>}
              <span><strong>{driver.name}</strong><small>{driver.type || "Driver"}</small></span>
              {driver.is_active !== false && <em>Active</em>}
              <span
                className="assigned-driver-remove"
                role="button"
                tabIndex={0}
                title={`Unassign ${driver.name}`}
                aria-label={`Unassign ${driver.name}`}
                onMouseDown={(event) => event.stopPropagation()}
                onClick={(event) => { event.stopPropagation(); onUnassignDriver?.(driver.id); }}
                onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onUnassignDriver?.(driver.id); } }}
              >×</span>
            </button>
          ))}
        </div>}
        {detailsVisible && selectedDriver ? (
          <div className="driver-details-content">
            <div className="driver-profile">
              <div className="driver-profile-photo">{selectedDriver.photo ? <img src={selectedDriver.photo} alt={selectedDriver.name} /> : <div className="driver-profile-placeholder">👤</div>}</div>
              <div className="driver-profile-info">
                <div className="driver-name-status"><h4>{selectedDriver.name}</h4>{selectedDriver.is_active !== false && <span className="driver-active"><span />Active</span>}</div>
                <div className="driver-role">{selectedDriver.type || "Driver"}</div>
                <div className="driver-contact"><span>☎ {selectedDriver.mobile || "—"}</span><span>Licence: {selectedDriver.driving_license_no || "—"}</span></div>
              </div>
            </div>
            <div className="driver-information-grid">
              <div className="driver-info-column"><h5>License Details</h5><div className="driver-info-row"><span>License No.</span><strong>{selectedDriver.driving_license_no || "—"}</strong></div><div className="driver-info-row"><span>Valid Until</span><strong>{selectedDriver.valid_until || "—"}</strong></div><div className="driver-info-row"><span>Driver Type</span><strong>{selectedDriver.type || "—"}</strong></div></div>
              <div className="driver-info-column"><h5>Assignment Info</h5><div className="driver-info-row"><span>Vehicle</span><strong>{vehicle?.registration_no || "—"}</strong></div><div className="driver-info-row"><span>Total Drivers</span><strong>{assignedDrivers.length}</strong></div><div className="driver-info-row"><span>Status</span><strong>{selectedDriver.is_active === false ? "Inactive" : "Active"}</strong></div></div>
            </div>
            {selectedDriver.documents && <div className="driver-document-area"><a href={selectedDriver.documents} target="_blank" rel="noreferrer" className="driver-document-link">View Driving Licence</a></div>}
          </div>
        ) : <div className="driver-empty-state"><div className="driver-empty-icon">👤</div><h4>No Driver Assigned</h4><p>Assign a driver from Driver Master.</p><button type="button" className="driver-blue-button" onClick={onOpenDriverMaster}>Open Driver Master</button></div>}
      </div>
    </section>
  );
}
