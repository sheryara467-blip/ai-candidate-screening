// ============================================================
// components/StatsCard.jsx
// Reusable stats card used on the admin dashboard overview.
// Displays a metric with icon, label, value, and optional trend.
// ============================================================

import Link from "next/link";

export default function StatsCard({ label, value, icon: Icon, color = "blue", subLabel = null, href = null }) {
  const colorMap = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    yellow: "bg-yellow-50 text-yellow-600",
    purple: "bg-purple-50 text-purple-600",
    red: "bg-red-50 text-red-600",
    gray: "bg-gray-50 text-gray-600",
  };

  const content = (
    <div className={`card p-6 flex items-start gap-4 ${href ? "hover:shadow-md transition-shadow cursor-pointer" : ""}`}>
      {/* Icon badge */}
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorMap[color]}`}>
        <Icon size={22} />
      </div>

      {/* Metric */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-500 font-medium">{label}</p>
        <p className="text-3xl font-bold text-gray-900 mt-0.5">
          {value ?? <span className="text-gray-400">—</span>}
        </p>
        {subLabel && (
          <p className="text-xs text-gray-400 mt-1">{subLabel}</p>
        )}
      </div>
    </div>
  );

  return href ? <Link href={href}>{content}</Link> : content;
}
