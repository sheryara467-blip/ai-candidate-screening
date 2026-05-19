// ============================================================
// components/analysis/ScoreBreakdownBar.jsx
// Shows the AI matching score components used in the analysis page.
// ============================================================

function Bar({ label, value, color }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1.5">
        <span className="font-medium text-gray-600">{label}</span>
        <span className="font-semibold text-gray-900">{(value || 0).toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(value || 0, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function ScoreBreakdownBar({
  cvScore = 0,
  skillScore = 0,
  experienceScore = 0,
  finalScore = 0,
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-semibold text-gray-900">Score Breakdown</h3>
          <p className="text-xs text-gray-400 mt-0.5">Weighted final score: {(finalScore || 0).toFixed(1)}%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <Bar label="CV Similarity" value={cvScore} color="bg-blue-500" />
        <Bar label="Skill Match" value={skillScore} color="bg-green-500" />
        <Bar label="Experience" value={experienceScore} color="bg-purple-500" />
      </div>
    </div>
  );
}
