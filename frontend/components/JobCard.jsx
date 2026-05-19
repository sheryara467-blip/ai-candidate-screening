// ============================================================
// components/JobCard.jsx
// Renders a single job card in the jobs list page.
// Shows status badge, skills preview, and action buttons.
// ============================================================

import Link from "next/link";
import { Pencil, Trash2, Users, RefreshCw, Calendar } from "lucide-react";

// Map status to badge class (defined in globals.css)
const STATUS_BADGE = {
  OPEN: "badge-open",
  DRAFT: "badge-draft",
  CLOSED: "badge-closed",
};

export default function JobCard({ job, onDelete, onRegenerate, isRegenerating }) {
  const statusBadge = STATUS_BADGE[job.status] || "badge-draft";

  // Format date to readable string
  const formattedDate = job.created_at
    ? new Date(job.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "—";

  // Preview first 3 skills from comma-separated string
  const skills = job.required_skills
    ? job.required_skills.split(",").map((s) => s.trim()).filter(Boolean)
    : [];
  const previewSkills = skills.slice(0, 3);
  const extraCount = skills.length - 3;

  return (
    <div className="card p-5 hover:shadow-md transition-shadow">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{job.title}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{job.department}</p>
        </div>
        <span className={statusBadge}>{job.status}</span>
      </div>

      {/* Skills tags */}
      {previewSkills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {previewSkills.map((skill) => (
            <span
              key={skill}
              className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-md font-medium"
            >
              {skill}
            </span>
          ))}
          {extraCount > 0 && (
            <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-md">
              +{extraCount} more
            </span>
          )}
        </div>
      )}

      {/* Meta row */}
      <div className="flex items-center gap-4 text-xs text-gray-400 mb-4">
        <span className="flex items-center gap-1">
          <Calendar size={12} />
          {formattedDate}
        </span>
        {job.experience && (
          <span>{job.experience}</span>
        )}
        {/* Sync warning badge */}
        {job.embedding_needs_update && (
          <span className="flex items-center gap-1 text-amber-500 font-medium">
            <RefreshCw size={11} />
            Sync pending
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 border-t border-gray-100 pt-4">
        {/* View Candidates */}
        <Link
          href={`/candidates/${job.id}`}
          className="btn-secondary text-xs py-1.5 flex-1 justify-center"
        >
          <Users size={13} />
          Candidates
        </Link>

        {/* Edit */}
        <Link
          href={`/jobs/${job.id}`}
          className="btn-secondary text-xs py-1.5 px-3"
        >
          <Pencil size={13} />
        </Link>

        {/* Regenerate Embedding */}
        <button
          onClick={() => onRegenerate(job.id)}
          disabled={isRegenerating}
          title="Regenerate Pinecone embedding"
          className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-40"
        >
          <RefreshCw size={13} className={isRegenerating ? "animate-spin" : ""} />
        </button>

        {/* Delete */}
        <button
          onClick={() => onDelete(job.id, job.title)}
          className="btn-danger text-xs py-1.5 px-3"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}