import React, { useMemo, useState } from "react";
import "./InsuranceMaster.css";

const initialCompanies = [
  {
    id: 1,
    name: "HDFC ERGO General Insurance",
    type: "General Insurance",
    code: "HEG",
    license: "1234567890",
    contact: "1800 270 7000",
    email: "customercare@hdfcergo.com",
    gst: "27AABCH2707H1Z8",
    status: "Active",
  },
  {
    id: 2,
    name: "IFFCO Tokio General Insurance",
    type: "General Insurance",
    code: "ITG",
    license: "9876543210",
    contact: "1800 103 5499",
    email: "info@iffcotokio.co.in",
    gst: "27AAACI9961H1Z1",
    status: "Active",
  },
  {
    id: 3,
    name: "ICICI Lombard General Insurance",
    type: "General Insurance",
    code: "ICL",
    license: "1122334455",
    contact: "1800 2666 2244",
    email: "customersupport@icicilombard.com",
    gst: "27AAACI7905G1Z0",
    status: "Active",
  },
  {
    id: 4,
    name: "Bajaj Allianz General Insurance",
    type: "General Insurance",
    code: "BAJ",
    license: "5566778899",
    contact: "1800 209 5858",
    email: "customercare@bajajallianz.co.in",
    gst: "27AAACB0118K1ZJ",
    status: "Active",
  },
  {
    id: 5,
    name: "United India Insurance",
    type: "General Insurance",
    code: "UII",
    license: "2233445566",
    contact: "1800 425 3333",
    email: "care@uiic.co.in",
    gst: "27AAACU0647F1Z3",
    status: "Active",
  },
  {
    id: 6,
    name: "TATA AIG General Insurance",
    type: "General Insurance",
    code: "TAT",
    license: "6677889900",
    contact: "1800 266 7788",
    email: "customerservice@tataaig.com",
    gst: "27AABCT1207B1Z6",
    status: "Active",
  },
  {
    id: 7,
    name: "National Insurance",
    type: "General Insurance",
    code: "NAT",
    license: "9988776655",
    contact: "1800 345 6111",
    email: "customercare@nationalinsurance.in",
    gst: "27AAACN0857F1Z9",
    status: "Active",
  },
  {
    id: 8,
    name: "Oriental Insurance",
    type: "General Insurance",
    code: "ORI",
    license: "4455667788",
    contact: "1800 233 2444",
    email: "info@orientalinsurance.co.in",
    gst: "27AAACO1575G1Z8",
    status: "Active",
  },
  {
    id: 9,
    name: "Shriram General Insurance",
    type: "General Insurance",
    code: "SHR",
    license: "7788990011",
    contact: "1800 103 1199",
    email: "care@shriramgi.com",
    gst: "27AAACS9589H1Z7",
    status: "Active",
  },
  {
    id: 10,
    name: "Royal Sundaram General Insurance",
    type: "General Insurance",
    code: "ROY",
    license: "9900112233",
    contact: "1800 425 4333",
    email: "customerservice@royalsundaram.in",
    gst: "27AAACR4520F1Z5",
    status: "Active",
  },
];

function InsuranceMaster() {
  const [companies, setCompanies] = useState(initialCompanies);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All Status");
  const [type, setType] = useState("All Types");

  const [showModal, setShowModal] = useState(false);
  const [viewCompany, setViewCompany] = useState(null);

  const [form, setForm] = useState({
    id: null,
    name: "",
    type: "General Insurance",
    code: "",
    license: "",
    contact: "",
    email: "",
    gst: "",
    status: "Active",
  });

  const filteredCompanies = useMemo(() => {
    return companies.filter((company) => {
      const searchText = search.toLowerCase();

      const matchesSearch =
        company.name.toLowerCase().includes(searchText) ||
        company.code.toLowerCase().includes(searchText) ||
        company.contact.includes(search);

      const matchesStatus =
        status === "All Status" || company.status === status;

      const matchesType =
        type === "All Types" || company.type === type;

      return matchesSearch && matchesStatus && matchesType;
    });
  }, [companies, search, status, type]);

  const resetFilters = () => {
    setSearch("");
    setStatus("All Status");
    setType("All Types");
  };

  const openAddModal = () => {
    setForm({
      id: null,
      name: "",
      type: "General Insurance",
      code: "",
      license: "",
      contact: "",
      email: "",
      gst: "",
      status: "Active",
    });

    setShowModal(true);
  };

  const openEditModal = (company) => {
    setForm(company);
    setShowModal(true);
  };

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const saveCompany = (e) => {
    e.preventDefault();

    if (!form.name.trim()) {
      alert("Company name is required");
      return;
    }

    if (form.id) {
      setCompanies((prev) =>
        prev.map((item) =>
          item.id === form.id ? form : item
        )
      );
    } else {
      setCompanies((prev) => [
        ...prev,
        {
          ...form,
          id: Date.now(),
        },
      ]);
    }

    setShowModal(false);
  };

  const deleteCompany = (id) => {
    if (!window.confirm("Are you sure you want to delete this company?")) {
      return;
    }

    setCompanies((prev) =>
      prev.filter((company) => company.id !== id)
    );
  };

  return (
    <div className="insurance-page">

      {/* HEADER */}
      <div className="page-header">
        <div className="page-title-wrapper">

          <div className="shield-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>

          <div>
            <h1>Insurance Company Master List</h1>
            <p>Manage insurance companies for claim processing</p>
          </div>

        </div>

        <button
          className="add-company-btn"
          onClick={openAddModal}
        >
          <span>+</span>
          Add Insurance Company
        </button>
      </div>

      {/* FILTER BAR */}
      <div className="filter-card">

        <div className="search-box">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-4-4" />
          </svg>

          <input
            type="text"
            placeholder="Search by company name, code, or contact number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option>All Status</option>
          <option>Active</option>
          <option>Inactive</option>
        </select>

        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          <option>All Types</option>
          <option>General Insurance</option>
          <option>Life Insurance</option>
        </select>

        <button className="search-btn">
          <span>⌕</span>
          Search
        </button>

        <button
          className="reset-btn"
          onClick={resetFilters}
        >
          ↻
          Reset
        </button>

      </div>

      {/* TABLE */}
      <div className="table-card">

        <div className="table-wrapper">
          <table>

            <thead>
              <tr>
                <th className="number-col">#</th>
                <th>Company Name ↕</th>
                <th>Code ↕</th>
                <th>License No. ↕</th>
                <th>Contact ↕</th>
                <th>Email ↕</th>
                <th>GST No. ↕</th>
                <th>Status ↕</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {filteredCompanies.length === 0 ? (
                <tr>
                  <td
                    colSpan="9"
                    className="no-data"
                  >
                    No insurance companies found
                  </td>
                </tr>
              ) : (
                filteredCompanies.map((company, index) => (
                  <tr key={company.id}>

                    <td>{index + 1}</td>

                    <td>
                      <div className="company-cell">

                        <div className="company-logo">
                          {company.name
                            .split(" ")
                            .slice(0, 2)
                            .map((word) => word[0])
                            .join("")
                            .toUpperCase()}
                        </div>

                        <div>
                          <div className="company-name">
                            {company.name}
                          </div>
                          <div className="company-type">
                            {company.type}
                          </div>
                        </div>

                      </div>
                    </td>

                    <td>{company.code}</td>
                    <td>{company.license}</td>
                    <td>{company.contact}</td>
                    <td>{company.email}</td>
                    <td>{company.gst}</td>

                    <td>
                      <span
                        className={
                          company.status === "Active"
                            ? "status active"
                            : "status inactive"
                        }
                      >
                        {company.status}
                      </span>
                    </td>

                    <td>
                      <div className="actions">

                        <button
                          className="icon-btn edit"
                          title="Edit"
                          onClick={() =>
                            openEditModal(company)
                          }
                        >
                          ✎
                        </button>

                        <button
                          className="icon-btn view"
                          title="View"
                          onClick={() =>
                            setViewCompany(company)
                          }
                        >
                          ◉
                        </button>

                        <button
                          className="icon-btn delete"
                          title="Delete"
                          onClick={() =>
                            deleteCompany(company.id)
                          }
                        >
                          ♡
                        </button>

                      </div>
                    </td>

                  </tr>
                ))
              )}
            </tbody>

          </table>
        </div>

        {/* PAGINATION */}
        <div className="table-footer">
          <span>
            Showing 1 to {filteredCompanies.length} of{" "}
            {filteredCompanies.length} entries
          </span>

          <div className="pagination">
            <button>‹</button>
            <button className="current">1</button>
            <button>2</button>
            <button>›</button>
          </div>
        </div>

      </div>

      {/* ADD / EDIT MODAL */}
      {showModal && (
        <div className="modal-overlay">

          <div className="insurance-modal">

            <div className="modal-header">
              <div>
                <h2>
                  {form.id
                    ? "Edit Insurance Company"
                    : "Add Insurance Company"}
                </h2>

                <p>
                  Enter insurance company details
                </p>
              </div>

              <button
                className="modal-close"
                onClick={() => setShowModal(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={saveCompany}>

              <div className="form-grid">

                <div className="form-group full">
                  <label>Company Name *</label>
                  <input
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    placeholder="Enter company name"
                  />
                </div>

                <div className="form-group">
                  <label>Company Code</label>
                  <input
                    name="code"
                    value={form.code}
                    onChange={handleChange}
                    placeholder="Enter code"
                  />
                </div>

                <div className="form-group">
                  <label>License No.</label>
                  <input
                    name="license"
                    value={form.license}
                    onChange={handleChange}
                    placeholder="Enter license number"
                  />
                </div>

                <div className="form-group">
                  <label>Contact</label>
                  <input
                    name="contact"
                    value={form.contact}
                    onChange={handleChange}
                    placeholder="Enter contact number"
                  />
                </div>

                <div className="form-group">
                  <label>Email</label>
                  <input
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="Enter email"
                  />
                </div>

                <div className="form-group">
                  <label>GST No.</label>
                  <input
                    name="gst"
                    value={form.gst}
                    onChange={handleChange}
                    placeholder="Enter GST number"
                  />
                </div>

                <div className="form-group">
                  <label>Insurance Type</label>
                  <select
                    name="type"
                    value={form.type}
                    onChange={handleChange}
                  >
                    <option>General Insurance</option>
                    <option>Life Insurance</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Status</label>
                  <select
                    name="status"
                    value={form.status}
                    onChange={handleChange}
                  >
                    <option>Active</option>
                    <option>Inactive</option>
                  </select>
                </div>

              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="save-btn"
                >
                  {form.id ? "Update Company" : "Save Company"}
                </button>
              </div>

            </form>

          </div>

        </div>
      )}

      {/* VIEW MODAL */}
      {viewCompany && (
        <div className="modal-overlay">

          <div className="insurance-modal view-modal">

            <div className="modal-header">
              <div>
                <h2>Insurance Company Details</h2>
                <p>Company information</p>
              </div>

              <button
                className="modal-close"
                onClick={() => setViewCompany(null)}
              >
                ×
              </button>
            </div>

            <div className="details-grid">

              <div>
                <small>Company Name</small>
                <strong>{viewCompany.name}</strong>
              </div>

              <div>
                <small>Company Code</small>
                <strong>{viewCompany.code}</strong>
              </div>

              <div>
                <small>License No.</small>
                <strong>{viewCompany.license}</strong>
              </div>

              <div>
                <small>Contact</small>
                <strong>{viewCompany.contact}</strong>
              </div>

              <div>
                <small>Email</small>
                <strong>{viewCompany.email}</strong>
              </div>

              <div>
                <small>GST No.</small>
                <strong>{viewCompany.gst}</strong>
              </div>

              <div>
                <small>Status</small>
                <strong>{viewCompany.status}</strong>
              </div>

            </div>

          </div>

        </div>
      )}

    </div>
  );
}

export default InsuranceMaster;