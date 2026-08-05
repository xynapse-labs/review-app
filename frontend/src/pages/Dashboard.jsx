import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { StatusBadge } from "../components/Badges";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "under_review", label: "Under Review" },
  { value: "changes_required", label: "Changes Required" },
  { value: "approved", label: "Approved" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [drawings, setDrawings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      const params = { status_filter: statusFilter || undefined };
      if (dateFrom) params.date_from = new Date(dateFrom).toISOString();
      if (dateTo) params.date_to = new Date(dateTo).toISOString();
      const list = await api.listDrawings(params);
      setDrawings(list);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, dateFrom, dateTo]);

  async function handleCreate(e) {
    e.preventDefault();
    setUploadError("");
    if (!title || !file) {
      setUploadError("Title and file are required");
      return;
    }
    setUploading(true);
    try {
      const drawing = await api.createDrawing(title, file);
      setTitle("");
      setFile(null);
      navigate(`/drawings/${drawing.id}`);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  const isDesigner = user.role === "designer";

  return (
    <div className="container">
      {isDesigner && (
        <div className="card">
          <h3>Submit a New Technical Drawing</h3>
          <form className="upload-form" onSubmit={handleCreate}>
            <div className="form-row" style={{ flex: 1, minWidth: 200 }}>
              <label>Title</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Bracket Mounting Plate" />
            </div>
            <div className="form-row">
              <label>File (PDF, PNG, or JPEG)</label>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={(e) => setFile(e.target.files[0])}
              />
            </div>
            <button type="submit" className="primary" disabled={uploading}>
              {uploading ? "Uploading..." : "Create Draft"}
            </button>
          </form>
          {uploadError && <div className="error-text">{uploadError}</div>}
          <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
            Creates a Draft. Open it afterward to submit it for review.
          </p>
        </div>
      )}

      <div className="card">
        <div className="flex-between">
          <h3>{isDesigner ? "My Submissions" : "Review Queue"}</h3>
        </div>
        <div className="filters">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <label className="muted">
            From <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="muted">
            To <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
        </div>

        {error && <div className="error-text">{error}</div>}
        {loading ? (
          <p className="muted">Loading...</p>
        ) : drawings.length === 0 ? (
          <p className="muted">No drawings match these filters.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Title</th>
                {!isDesigner && <th>Designer</th>}
                <th>Status</th>
                <th>Revision</th>
                <th>Open Change Requests</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {drawings.map((d) => (
                <tr key={d.id} className="clickable" onClick={() => navigate(`/drawings/${d.id}`)}>
                  <td>{d.title}</td>
                  {!isDesigner && <td>{d.designer.display_name}</td>}
                  <td>
                    <StatusBadge status={d.status} />
                  </td>
                  <td>{d.version_count > 0 ? `Rev ${revLetter(d.latest_version_number)}` : "—"}</td>
                  <td>{d.open_change_requests > 0 ? d.open_change_requests : "—"}</td>
                  <td>{new Date(d.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function revLetter(n) {
  let num = n - 1;
  let letters = "";
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const rem = num % 26;
    letters = String.fromCharCode(65 + rem) + letters;
    num = Math.floor(num / 26);
    if (num === 0) break;
    num -= 1;
  }
  return letters;
}
