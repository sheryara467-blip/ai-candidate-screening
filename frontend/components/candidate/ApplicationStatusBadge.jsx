// ============================================================
// components/candidate/ApplicationStatusBadge.jsx — NEW Phase 2
// Reusable badge that shows application status with color coding.
// Used on the status page and candidate dashboard.
// ============================================================

import { CheckCircle, Clock, Star, XCircle } from "lucide-react";

const STATUS_CONFIG = {
  SUBMITTED: {
    label:  "Submitted",
    bg:     "bg-blue-50",
    text:   "text-blue-700",
    border: "border-blue-200",
    Icon:   Clock,
    desc:   "Your application has been received.",
  },
  UNDER_REVIEW: {
    label:  "Under Review",
    bg:     "bg-yellow-50",
    text:   "text-yellow-700",
    border: "border-yellow-200",
    Icon:   Clock,
    desc:   "Our team is currently reviewing your application.",
  },
  SHORTLISTED: {
    label:  "Shortlisted",
    bg:     "bg-green-50",
    text:   "text-green-700",
    border: "border-green-200",
    Icon:   Star,
    desc:   "Congratulations! You have been shortlisted.",
  },
  REJECTED: {
    label:  "Not Selected",
    bg:     "bg-red-50",
    text:   "text-red-600",
    border: "border-red-200",
    Icon:   XCircle,
    desc:   "Unfortunately you were not selected for this role.",
  },
};

// ============================================================
// Inline badge variant — used in tables / list rows
// ============================================================
export function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.SUBMITTED;
  const Icon = cfg.Icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}
    >
      <Icon size={12} />
      {cfg.label}
    </span>
  );
}

// ============================================================
// Card variant — used on the confirmation / status detail page
// ============================================================
export default function ApplicationStatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.SUBMITTED;
  const Icon = cfg.Icon;

  return (
    <div className={`rounded-xl border p-5 flex items-start gap-4 ${cfg.bg} ${cfg.border}`}>
      <div className={`w-10 h-10 rounded-full flex items-center justify-center bg-white ${cfg.text} shrink-0`}>
        <Icon size={20} />
      </div>
      <div>
        <p className={`font-semibold text-base ${cfg.text}`}>{cfg.label}</p>
        <p className="text-sm text-gray-600 mt-0.5">{cfg.desc}</p>
      </div>
    </div>
  );
}