const STATUS_LABELS = {
  draft: "Draft",
  under_review: "Under Review",
  changes_required: "Changes Required",
  approved: "Approved",
};

const TAG_LABELS = {
  request_change: "Request Change",
  general_feedback: "General Feedback",
};

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

export function TagBadge({ tag }) {
  return <span className={`tag tag-${tag}`}>{TAG_LABELS[tag] || tag}</span>;
}
