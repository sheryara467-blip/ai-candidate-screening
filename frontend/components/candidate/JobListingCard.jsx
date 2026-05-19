// ============================================================
// components/candidate/JobListingCard.jsx  —  NEW in Phase 2
// Public-facing job card displayed on the /careers page.
// Different from admin JobCard.jsx — no delete/edit/sync buttons.
// ============================================================

import Link from "next/link";
import { MapPin, Clock, GraduationCap, ArrowRight } from "lucide-react";

export default function JobListingCard({ job }) {
  // Show first 130 characters of description as preview
  const descPreview = job.description
    ? job.description.slice(0, 130) + (job.description.length > 130 ? "..." : "")
    : "";

  // Parse comma-separated skills into an array
  const skills = job.required_skills
    ? job.required_skills.split(",").map((s) => s.trim()).filter(Boolean)
    : [];
  const previewSkills = skills.slice(0, 4);
  const extraCount   = skills.length - 4;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md hover:border-blue-200 transition-all group">

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h3 className="font-bold text-gray-900 text-lg group-hover:text-blue-600 transition-colors">
            {job.title}
          </h3>
          <p className="text-sm text-gray-500 mt-0.5 font-medium">{job.department}</p>
        </div>
        {/* OPEN badge */}
        <span className="shrink-0 px-2.5 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
          Hiring
        </span>
      </div>

      {/* Description preview */}
      <p className="text-sm text-gray-600 leading-relaxed mb-4">{descPreview}</p>

      {/* Meta row */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-400 mb-4">
        {job.experience && (
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {job.experience}
          </span>
        )}
        {job.education && (
          <span className="flex items-center gap-1">
            <GraduationCap size={12} />
            {job.education}
          </span>
        )}
      </div>

      {/* Skills chips */}
      {previewSkills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-5">
          {previewSkills.map((skill) => (
            <span
              key={skill}
              className="px-2.5 py-1 bg-blue-50 text-blue-700 text-xs rounded-lg font-medium"
            >
              {skill}
            </span>
          ))}
          {extraCount > 0 && (
            <span className="px-2.5 py-1 bg-gray-100 text-gray-400 text-xs rounded-lg">
              +{extraCount} more
            </span>
          )}
        </div>
      )}

      {/* CTA buttons */}
      <div className="flex gap-3 border-t border-gray-100 pt-4">
        <Link
          href={`/careers/${job.id}`}
          className="flex-1 text-center py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
        >
          View Details
        </Link>
        <Link
          href={`/apply/${job.id}`}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Apply Now
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}