// ============================================================
// EXACT FILE LOCATION: frontend/pages/admin/analysis/[candidateId].js
// ============================================================
// PURPOSE: Admin page showing full AI analysis for one candidate.
// Shows: match score, skill gap, score breakdown, AI summary,
// strengths, weaknesses, per-skill table.
//
// URL example: /admin/analysis/3?jobId=1
// ============================================================

import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "../../../components/Layout";
import MatchScoreCard from "../../../components/analysis/MatchScoreCard";
import SkillGapPanel from "../../../components/analysis/SkillGapPanel";
import ScoreBreakdownBar from "../../../components/analysis/ScoreBreakdownBar";
import {
  getMatchResult,
  runMatch,
  processResume,
  generateCandidateEmbedding,
  generateJobEmbedding,
} from "../../../services/api";
import toast from "react-hot-toast";
import {
  ArrowLeft, RefreshCw, Brain, CheckCircle,
  AlertCircle, User, Briefcase, Zap,
} from "lucide-react";

export default function CandidateAnalysisPage() {
  const router = useRouter();
  const { candidateId, jobId } = router.query;

  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [running,   setRunning]   = useState(false);

  // Fetch existing match result on load
  useEffect(() => {
    if (!candidateId || !jobId) return;
    fetchResult();
  }, [candidateId, jobId]);

  const fetchResult = async () => {
    try {
      setLoading(true);
      const data = await getMatchResult(candidateId, jobId);
      setResult(data);
    } catch (err) {
      // No result yet — that's fine, show the run button
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Full AI pipeline: process → embed → match
  // Runs all three steps in sequence
  // ============================================================
  const handleRunFullPipeline = async () => {
    setRunning(true);
    try {
      // Step 1: Process resume (extract text + skills)
      toast.loading("Step 1/3: Extracting resume...", { id: "pipeline" });
      await processResume(candidateId);

      // Step 2: Generate embeddings for candidate + job
      toast.loading("Step 2/3: Generating embeddings...", { id: "pipeline" });
      await generateCandidateEmbedding(candidateId);
      await generateJobEmbedding(jobId);

      // Step 3: Run semantic matching
      toast.loading("Step 3/3: Running AI matching...", { id: "pipeline" });
      const data = await runMatch(candidateId, jobId, true);
      setResult(data);

      toast.success("AI analysis complete!", { id: "pipeline" });
    } catch (err) {
      toast.error("Pipeline failed: " + (err.userMessage || "Unknown error"), { id: "pipeline" });
    } finally {
      setRunning(false);
    }
  };

  // Parse helpers
  const toList = (s) => s ? s.split(",").map(x => x.trim()).filter(Boolean) : [];
  const pipeToList = (s) => s ? s.split("|").map(x => x.trim()).filter(Boolean) : [];

  return (
    <Layout title="AI Candidate Analysis">

      {/* Back link */}
      <Link
        href={jobId ? `/candidates/${jobId}` : "/jobs"}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft size={15} /> Back to Candidates
      </Link>

      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Brain size={20} className="text-blue-600" />
            AI Analysis Report
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            Candidate #{candidateId} · Job #{jobId}
          </p>
        </div>

        {/* Run / Re-run button */}
        <button
          onClick={handleRunFullPipeline}
          disabled={running}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {running ? (
            <><RefreshCw size={15} className="animate-spin" /> Running...</>
          ) : (
            <><Zap size={15} /> {result ? "Re-run Analysis" : "Run AI Analysis"}</>
          )}
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse h-48" />
          ))}
        </div>
      )}

      {/* No result yet */}
      {!loading && !result && (
        <div className="text-center py-20">
          <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Brain size={28} className="text-blue-400" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-1">No analysis yet</h3>
          <p className="text-gray-400 text-sm mb-6">
            Click "Run AI Analysis" to process the resume, generate embeddings,
            and compute the semantic match score.
          </p>
          <button
            onClick={handleRunFullPipeline}
            disabled={running}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <Zap size={16} />
            Run AI Analysis
          </button>
        </div>
      )}

      {/* Full analysis result */}
      {!loading && result && (
        <div className="space-y-6">

          {/* Row 1: Score card + candidate/job info */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Circular match score */}
            <MatchScoreCard
              score={result.final_match_score}
              recommendation={result.recommendation}
            />

            {/* Candidate + job summary */}
            <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1 flex items-center gap-1">
                    <User size={11} /> Candidate
                  </p>
                  <p className="font-bold text-gray-900">{result.candidate_name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">ID #{result.candidate_profile_id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1 flex items-center gap-1">
                    <Briefcase size={11} /> Position
                  </p>
                  <p className="font-bold text-gray-900">{result.job_title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">Job #{result.job_id}</p>
                </div>
              </div>

              {/* AI Summary */}
              {result.ai_summary && (
                <div className="mt-5 pt-4 border-t border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                    AI Summary
                  </p>
                  <p className="text-sm text-gray-600 leading-relaxed">{result.ai_summary}</p>
                </div>
              )}
            </div>
          </div>

          {/* Row 2: Score breakdown */}
          <ScoreBreakdownBar
            cvScore={result.cv_similarity_score}
            skillScore={result.skill_match_score}
            experienceScore={result.experience_score}
            finalScore={result.final_match_score}
          />

          {/* Row 3: Skill gap */}
          <SkillGapPanel
            matchedSkills={result.matched_skills || []}
            missingSkills={result.missing_skills || []}
          />

          {/* Row 4: Strengths + Weaknesses */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

            {/* Strengths */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                <CheckCircle size={13} /> Strengths
              </p>
              {(result.strengths || []).length === 0 ? (
                <p className="text-xs text-gray-400">None identified</p>
              ) : (
                <ul className="space-y-2">
                  {(result.strengths || []).map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="w-1.5 h-1.5 bg-green-400 rounded-full mt-1.5 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Weaknesses */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                <AlertCircle size={13} /> Areas to Improve
              </p>
              {(result.weaknesses || []).length === 0 ? (
                <p className="text-xs text-green-600 font-medium">No weaknesses identified</p>
              ) : (
                <ul className="space-y-2">
                  {(result.weaknesses || []).map((w, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="w-1.5 h-1.5 bg-red-400 rounded-full mt-1.5 shrink-0" />
                      {w}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Row 5: Per-skill breakdown table */}
          {result.skill_analysis && result.skill_analysis.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <p className="text-sm font-semibold text-gray-900">Per-Skill Breakdown</p>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="text-left px-5 py-3">Skill</th>
                    <th className="text-left px-5 py-3">Required</th>
                    <th className="text-left px-5 py-3">Match</th>
                    <th className="text-left px-5 py-3">Similarity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.skill_analysis.map((skill, i) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3 font-medium text-gray-800">{skill.skill_name}</td>
                      <td className="px-5 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${skill.is_required ? "bg-red-50 text-red-600" : "bg-gray-100 text-gray-500"}`}>
                          {skill.is_required ? "Required" : "Optional"}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {skill.is_matched ? (
                          <span className="flex items-center gap-1 text-green-600 font-medium">
                            <CheckCircle size={13} /> Matched
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-red-500">
                            <AlertCircle size={13} /> Missing
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{ width: `${(skill.similarity || 0) * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-400">
                            {((skill.similarity || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

        </div>
      )}
    </Layout>
  );
}