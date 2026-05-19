// ============================================================
// EXACT FILE LOCATION: frontend/components/analysis/SkillGapPanel.jsx
// ============================================================
// PURPOSE: Shows two columns — matched skills (green) and
// missing skills (red) — for a candidate match result.
// ============================================================

import { CheckCircle, XCircle } from "lucide-react";

export default function SkillGapPanel({ matchedSkills = [], missingSkills = [] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

      {/* Matched skills */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4">
        <p className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <CheckCircle size={13} /> Matched Skills ({matchedSkills.length})
        </p>
        {matchedSkills.length === 0 ? (
          <p className="text-xs text-gray-400">No matched skills</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-lg"
              >
                {skill}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Missing skills */}
      <div className="bg-red-50 border border-red-200 rounded-xl p-4">
        <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <XCircle size={13} /> Missing Skills ({missingSkills.length})
        </p>
        {missingSkills.length === 0 ? (
          <p className="text-xs text-green-600 font-medium">No missing skills 🎉</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {missingSkills.map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-lg"
              >
                {skill}
              </span>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}