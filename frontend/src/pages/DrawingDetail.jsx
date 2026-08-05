import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { StatusBadge, TagBadge } from "../components/Badges";

function buildTree(comments) {
  const byId = new Map(comments.map((c) => [c.id, { ...c, replies: [] }]));
  const roots = [];
  for (const c of byId.values()) {
    if (c.parent_id && byId.has(c.parent_id)) {
      byId.get(c.parent_id).replies.push(c);
    } else {
      roots.push(c);
    }
  }
  return roots;
}

export default function DrawingDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [drawing, setDrawing] = useState(null);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [commentBody, setCommentBody] = useState("");
  const [commentTag, setCommentTag] = useState("general_feedback");
  const [locationRef, setLocationRef] = useState("");
  const [replyTo, setReplyTo] = useState(null);

  const [newVersionFile, setNewVersionFile] = useState(null);
  const [statusNote, setStatusNote] = useState("");

  async function refresh(keepSelection = true) {
    try {
      const d = await api.getDrawing(id);
      setDrawing(d);
      if (!keepSelection || !selectedVersionId) {
        setSelectedVersionId(d.versions[d.versions.length - 1]?.id ?? null);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (error) {
    return (
      <div className="container">
        <p className="error-text">{error}</p>
        <Link to="/">Back to dashboard</Link>
      </div>
    );
  }
  if (!drawing) {
    return (
      <div className="container">
        <p className="muted">Loading...</p>
      </div>
    );
  }

  const isOwner = drawing.designer.id === user.id;
  const isReviewer = user.role === "reviewer";
  const version = drawing.versions.find((v) => v.id === selectedVersionId) || drawing.versions[drawing.versions.length - 1];
  const canSubmit = isOwner && ["draft", "changes_required"].includes(drawing.status);
  const canReview = isReviewer && !isOwner && drawing.status === "under_review";
  const canComment = isOwner || isReviewer;

  async function handleSubmitForReview() {
    setBusy(true);
    setError("");
    try {
      await api.submitDrawing(drawing.id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleUploadVersion(e) {
    e.preventDefault();
    if (!newVersionFile) return;
    setBusy(true);
    setError("");
    try {
      await api.addVersion(drawing.id, newVersionFile);
      setNewVersionFile(null);
      await refresh(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleStatusChange(newStatus) {
    setBusy(true);
    setError("");
    try {
      await api.changeStatus(drawing.id, version.id, newStatus, statusNote || undefined);
      setStatusNote("");
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAddComment(e) {
    e.preventDefault();
    if (!commentBody.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.addComment(version.id, {
        body: commentBody,
        tag: commentTag,
        location_ref: locationRef || undefined,
        parent_id: replyTo,
      });
      setCommentBody("");
      setLocationRef("");
      setCommentTag("general_feedback");
      setReplyTo(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleResolve(commentId) {
    setBusy(true);
    setError("");
    try {
      await api.resolveComment(commentId);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const tree = version ? buildTree(version.comments) : [];

  return (
    <div className="container">
      <Link to="/">&larr; Back to dashboard</Link>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="flex-between">
          <div>
            <h2 style={{ marginBottom: 4 }}>{drawing.title}</h2>
            <div className="muted">Designer: {drawing.designer.display_name}</div>
          </div>
          <StatusBadge status={drawing.status} />
        </div>

        {error && <div className="error-text" style={{ marginTop: 10 }}>{error}</div>}

        <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {canSubmit && (
            <button className="primary" disabled={busy} onClick={handleSubmitForReview}>
              Submit for Review
            </button>
          )}
          {isOwner && (
            <form onSubmit={handleUploadVersion} style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={(e) => setNewVersionFile(e.target.files[0])}
              />
              <button type="submit" disabled={busy || !newVersionFile}>
                Upload New Version
              </button>
            </form>
          )}
          {canReview && (
            <>
              <input
                placeholder="Note (optional)"
                value={statusNote}
                onChange={(e) => setStatusNote(e.target.value)}
                style={{ minWidth: 220 }}
              />
              <button className="success" disabled={busy} onClick={() => handleStatusChange("approved")}>
                Approve
              </button>
              <button className="danger" disabled={busy} onClick={() => handleStatusChange("changes_required")}>
                Request Changes
              </button>
            </>
          )}
          {isReviewer && isOwner && (
            <span className="muted">You cannot review your own submission.</span>
          )}
        </div>
      </div>

      <div className="card">
        <p className="section-title">Version History</p>
        <div className="tabs">
          {drawing.versions.map((v) => (
            <button
              key={v.id}
              className={`tab ${v.id === version?.id ? "active" : ""}`}
              onClick={() => setSelectedVersionId(v.id)}
            >
              Rev {v.revision_letter}
              {v.superseded && <span className="superseded-mark"> (superseded)</span>}
            </button>
          ))}
        </div>

        {version && (
          <>
            <div className="viewer-frame">
              {version.file_type === "pdf" ? (
                <iframe
                  title="drawing-file"
                  src={api.fileUrl(version.file_url)}
                  style={{ width: "100%", height: "100%", border: "none" }}
                />
              ) : (
                <img src={api.fileUrl(version.file_url)} alt={version.original_filename} />
              )}
            </div>
            <p className="muted" style={{ marginTop: 8 }}>
              {version.original_filename} &middot; uploaded by {version.uploader.display_name} on{" "}
              {new Date(version.uploaded_at).toLocaleString()}
            </p>
          </>
        )}
      </div>

      <div className="card">
        <p className="section-title">
          Feedback on Rev {version?.revision_letter}
        </p>

        {tree.length === 0 && <p className="muted">No comments on this version yet.</p>}

        {tree.map((c) => (
          <CommentNode
            key={c.id}
            comment={c}
            canComment={canComment}
            onReply={setReplyTo}
            onResolve={handleResolve}
          />
        ))}

        {canComment && (
          <form onSubmit={handleAddComment} style={{ marginTop: 12 }}>
            {replyTo && (
              <div className="muted" style={{ marginBottom: 6 }}>
                Replying to comment #{replyTo}{" "}
                <button type="button" onClick={() => setReplyTo(null)} style={{ fontSize: 12, padding: "1px 6px" }}>
                  cancel
                </button>
              </div>
            )}
            <div className="form-row">
              <textarea
                rows={3}
                placeholder="Add a comment..."
                value={commentBody}
                onChange={(e) => setCommentBody(e.target.value)}
              />
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
              <div className="form-row" style={{ marginBottom: 0 }}>
                <label>Tag</label>
                <select value={commentTag} onChange={(e) => setCommentTag(e.target.value)}>
                  <option value="general_feedback">General Feedback</option>
                  <option value="request_change">Request Change</option>
                </select>
              </div>
              <div className="form-row" style={{ marginBottom: 0, flex: 1 }}>
                <label>Reference (optional)</label>
                <input
                  placeholder="e.g. sheet 1, top-left hole pattern"
                  value={locationRef}
                  onChange={(e) => setLocationRef(e.target.value)}
                />
              </div>
              <button type="submit" className="primary" disabled={busy}>
                {replyTo ? "Post Reply" : "Add Comment"}
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="card">
        <p className="section-title">Compliance / Audit Log</p>
        {drawing.status_events.map((ev) => (
          <div className="audit-item" key={ev.id}>
            <strong>{ev.actor.display_name}</strong> ({ev.actor.role}) changed status
            {ev.old_status ? ` from ${ev.old_status} to ${ev.new_status}` : ` to ${ev.new_status}`}
            {ev.note && <> &mdash; {ev.note}</>}
            <div className="muted">{new Date(ev.created_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CommentNode({ comment, canComment, onReply, onResolve, depth = 0 }) {
  return (
    <>
      <div className={`comment ${depth > 0 ? "reply" : ""}`}>
        <div className="comment-header">
          <span className="comment-author">{comment.author.display_name}</span>
          <TagBadge tag={comment.tag} />
          {comment.resolved && <span className="resolved-mark">Resolved</span>}
          <span className="comment-time">{new Date(comment.created_at).toLocaleString()}</span>
        </div>
        {comment.location_ref && <div className="comment-location">Ref: {comment.location_ref}</div>}
        <div className="comment-body">{comment.body}</div>
        <div className="comment-actions">
          {canComment && (
            <button style={{ fontSize: 12, padding: "2px 8px" }} onClick={() => onReply(comment.id)}>
              Reply
            </button>
          )}
          {canComment && comment.tag === "request_change" && !comment.resolved && (
            <button style={{ fontSize: 12, padding: "2px 8px" }} onClick={() => onResolve(comment.id)}>
              Mark Resolved
            </button>
          )}
        </div>
      </div>
      {comment.replies.map((r) => (
        <CommentNode
          key={r.id}
          comment={r}
          canComment={canComment}
          onReply={onReply}
          onResolve={onResolve}
          depth={depth + 1}
        />
      ))}
    </>
  );
}
