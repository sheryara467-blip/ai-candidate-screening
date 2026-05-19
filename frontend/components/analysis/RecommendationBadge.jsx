// ============================================================
// EXACT FILE LOCATION: frontend/components/analysis/ScoreBreakdownBar.jsx
// ============================================================
// PURPOSE: Shows the three scoring components as labeled
// progress bars: CV Similarity, Skill Match, Experience.
// ============================================================

function Bar({ label, value, weight, color }) {
  const colorMap = {
    blue:   "bg-blue-500",
    green:  "bg-green-500",
    purple: "bg-purple-500",
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-600 font-medium">{label}</span>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">weight {weight}</span>
          <span className="text-sm font-bold text-gray-800">{value?.toFixed(1)}%</span>
        </div>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorMap[color]} rounded-full transition-all duration-700`}
          style={{ width: `${Math.min(value || 0, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function ScoreBreakdownBar({ cvScore, skillScore, experienceScore, finalScore }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <p className="text-sm font-semibold text-gray-700 mb-2">Score Breakdown</p>

      <Bar label="CV Semantic Similarity" value={cvScore}         weight="×0.4" color="blue"   />
      <Bar label="Skill Match"            value={skillScore}      weight="×0.4" color="green"  />
      <Bar label="Experience Match"       value={experienceScore} weight="×0.2" color="purple" />

      {/* Final score */}
      <div className="pt-3 border-t border-gray-100 flex justify-between items-center">
        <span className="text-sm font-bold text-gray-900">Final Match Score</span>
        <span className="text-xl font-extrabold text-gray-900">
          {finalScore?.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}