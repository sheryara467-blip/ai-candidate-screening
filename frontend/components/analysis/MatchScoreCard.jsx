// ============================================================
// EXACT FILE LOCATION: frontend/components/analysis/MatchScoreCard.jsx
// ============================================================
// PURPOSE: Displays the AI match score as a circular gauge
// with color coding based on score range.
// Used on the admin candidate analysis page.
// ============================================================

export default function MatchScoreCard({ score, recommendation }) {

  // Color thresholds matching backend RecommendationLevel
  const getScoreColor = (s) => {
    if (s >= 80) return { ring: "text-green-500",  bg: "bg-green-50",  label: "text-green-700"  };
    if (s >= 60) return { ring: "text-blue-500",   bg: "bg-blue-50",   label: "text-blue-700"   };
    if (s >= 40) return { ring: "text-yellow-500", bg: "bg-yellow-50", label: "text-yellow-700" };
    return             { ring: "text-red-500",    bg: "bg-red-50",    label: "text-red-700"    };
  };

  const colors = getScoreColor(score);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  // Clamp score 0–100 for the arc calculation
  const progress = Math.min(Math.max(score, 0), 100);
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const REC_LABELS = {
    HIGHLY_RECOMMENDED: "Highly Recommended",
    RECOMMENDED:        "Recommended",
    NEEDS_IMPROVEMENT:  "Needs Improvement",
    NOT_RECOMMENDED:    "Not Recommended",
  };

  return (
    <div className={`rounded-xl border p-6 flex flex-col items-center ${colors.bg}`}>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
        AI Match Score
      </p>

      {/* Circular SVG gauge */}
      <div className="relative w-36 h-36 mb-4">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
          {/* Background ring */}
          <circle
            cx="64" cy="64" r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="10"
          />
          {/* Progress ring */}
          <circle
            cx="64" cy="64" r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`transition-all duration-700 ${colors.ring}`}
          />
        </svg>
        {/* Score text in center */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-extrabold ${colors.ring}`}>
            {score?.toFixed(0)}%
          </span>
          <span className="text-xs text-gray-400 mt-0.5">Match</span>
        </div>
      </div>

      {/* Recommendation label */}
      {recommendation && (
        <span className={`text-sm font-semibold ${colors.label}`}>
          {REC_LABELS[recommendation] || recommendation}
        </span>
      )}
    </div>
  );
}