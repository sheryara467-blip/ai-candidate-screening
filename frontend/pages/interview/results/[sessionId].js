// ============================================================
// EXACT FILE LOCATION: frontend/pages/interview/results/[sessionId].js
// ============================================================
// PURPOSE: Admin view of a completed interview evaluation.
// Shows: interview score, per-question breakdown, AI feedback,
// strengths, weaknesses, and final recommendation.
//
// URL: /interview/results/{sessionId}
// Linked from the candidates/[jobId].js page.
// ============================================================

import { useEffect, useState } from "react";
import { useRouter }  from "next/router";
import Link           from "next/link";
import Layout         from "../../../components/Layout";
import { getInterviewResults } from "../../../services/api";
import toast from "react-hot-toast";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  MessageSquare,
  Star,
  TrendingUp,
  AlertCircle,
  User,
  Briefcase,
} from "lucide-react";

// Per-score color helper
function scoreColor(score) {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-blue-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-500";
}

// Recommendation badge style
const REC_STYLE = {
  Excellent: { bg: "bg-green-100",  text: "text-green-800",  border: "border-green-200"  },
  Good:      { bg: "bg-blue-100",   text: "text-blue-800",   border: "border-blue-200"   },
  Average:   { bg: "bg-yellow-100", text: "text-yellow-800", border: "border-yellow-200" },
  Weak:      { bg: "bg-red-100",    text: "text-red-700",    border: "border-red-200"    },
};

// Score progress bar
function ScoreBar({ label, value }) {
  const pct = Math.min(Math.max(value || 0, 0), 100);
  const color =
    pct >= 80 ? "bg-green-500" :
    pct >= 60 ? "bg-blue-500"  :
    pct >= 40 ? "bg-yellow-500" :
               "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span className="truncate max-w-xs">{label}</span>
        <span className={`font-bold ml-2 ${scoreColor(pct)}`}>{pct.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function InterviewResultsPage() {
  const router          = useRouter();
  const { sessionId }   = router.query;
  const [result,   setResult]   = useState(null);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    const fetchResults = async () => {
      try {
        const data = await getInterviewResults(sessionId);
        setResult(data);
      } catch (err) {
        toast.error("Failed to load interview results");
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, [sessionId]);

  const recStyle = result ? (REC_STYLE[result.recommendation] || REC_STYLE.Average) : null;

  // ── Loading skeleton ──────────────────────────────────────
  if (loading) {
    return (
      <Layout title="Interview Results">
        <div className="max-w-3xl space-y-5">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-6 animate-pulse h-28" />
          ))}
        </div>
      </Layout>
    );
  }

  if (!result) {
    return (
      <Layout title="Interview Results">
        <div className="text-center py-20">
          <AlertCircle size={32} className="text-gray-400 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No results found for this session.</p>
          <Link href="/jobs" className="btn-primary mt-4 inline-flex">Back to Jobs</Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Interview Results">

      {/* Back link */}
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft size={15} /> Back to Jobs
      </Link>

      <div className="max-w-3xl space-y-6">

        {/* ── HEADER CARD ── */}
        <div className="card p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">

            {/* Candidate + Job info */}
            <div className="space-y-2">
              <p className="text-xs text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
                <User size={12} /> Candidate
              </p>
              <h2 className="text-xl font-bold text-gray-900">{result.candidate_name}</h2>

              <p className="text-xs text-gray-400 uppercase tracking-wide flex items-center gap-1.5 mt-2">
                <Briefcase size={12} /> Position
              </p>
              <p className="font-semibold text-gray-700">{result.job_title}</p>
            </div>

            {/* Score + Recommendation */}
            <div className="text-right shrink-0">
              <p className={`text-5xl font-extrabold ${scoreColor(result.interview_score)}`}>
                {result.interview_score?.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-400 mt-1">Interview Score</p>

              {recStyle && (
                <span className={`inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full text-xs font-semibold border ${recStyle.bg} ${recStyle.text} ${recStyle.border}`}>
                  <Star size={11} />
                  {result.recommendation}
                </span>
              )}
            </div>
          </div>

          {/* Overall AI feedback */}
          {result.overall_feedback && (
            <div className="mt-5 pt-4 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <MessageSquare size={12} /> AI Summary
              </p>
              <p className="text-sm text-gray-600 leading-relaxed">{result.overall_feedback}</p>
            </div>
          )}
        </div>

        {/* ── STRENGTHS + WEAKNESSES ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

          {/* Strengths */}
          <div className="card p-5">
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
          <div className="card p-5">
            <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
              <XCircle size={13} /> Areas to Improve
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

        {/* ── PER-QUESTION BREAKDOWN ── */}
        {result.question_analysis && result.question_analysis.length > 0 && (
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <TrendingUp size={16} className="text-blue-600" />
              <p className="font-semibold text-gray-900">Question-by-Question Breakdown</p>
            </div>

            <div className="divide-y divide-gray-100">
              {result.question_analysis.map((item, idx) => (
                <div key={idx} className="p-6">

                  {/* Question number + score */}
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex-1">
                      <span className="text-xs font-bold text-gray-400 uppercase tracking-wide">
                        Q{idx + 1}
                      </span>
                      <p className="text-sm font-semibold text-gray-900 mt-0.5">
                        {item.question}
                      </p>
                    </div>
                    <span className={`text-lg font-extrabold shrink-0 ${scoreColor(item.answer_score)}`}>
                      {item.answer_score?.toFixed(0)}%
                    </span>
                  </div>

                  {/* Score bar */}
                  <div className="mb-3">
                    <ScoreBar label="Answer Score" value={item.answer_score} />
                  </div>

                  {/* Candidate's answer */}
                  <div className="bg-gray-50 rounded-lg p-3 mb-3">
                    <p className="text-xs text-gray-400 font-medium mb-1">Candidate's Answer</p>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {item.answer || <span className="italic text-gray-400">No answer provided</span>}
                    </p>
                  </div>

                  {/* AI feedback */}
                  {item.feedback && (
                    <div className="flex items-start gap-2">
                      <MessageSquare size={13} className="text-blue-500 mt-0.5 shrink-0" />
                      <p className="text-xs text-gray-500 leading-relaxed italic">
                        {item.feedback}
                      </p>
                    </div>
                  )}

                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}