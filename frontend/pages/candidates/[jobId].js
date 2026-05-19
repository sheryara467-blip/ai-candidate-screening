// ============================================================
// EXACT FILE LOCATION: frontend/pages/candidates/[jobId].js
// ============================================================
// UPDATED:
//   1. Shortlist / Reject buttons on every candidate card
//   2. Correct ID mapping: candidate_profile_id for AI ops
//   3. Interview button shown when session exists
//   4. Dedup fix: lookup uses candidate_profile_id not name
// ============================================================

import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "../../components/Layout";
import {
  getCandidatesForJob,
  getJob,
  getJobMatchResults,
  getJobInterviewSessions,
  processResume,
  generateCandidateEmbedding,
  generateJobEmbedding,
  runBulkMatch,
  updateCandidateStatus,
} from "../../services/api";
import toast from "react-hot-toast";
import {
  ArrowLeft, Users, RefreshCw, Mail,
  ChevronDown, ChevronUp, Brain, MessageSquare,
  AlertTriangle, CheckCircle, XCircle, Clock,
} from "lucide-react";

const REC_STYLE = {
  HIGHLY_RECOMMENDED: { bg: "bg-green-100",  text: "text-green-800",  label: "Highly Recommended" },
  RECOMMENDED:        { bg: "bg-blue-100",   text: "text-blue-800",   label: "Recommended"        },
  NEEDS_IMPROVEMENT:  { bg: "bg-yellow-100", text: "text-yellow-800", label: "Needs Improvement"  },
  NOT_RECOMMENDED:    { bg: "bg-red-100",    text: "text-red-600",    label: "Not Recommended"    },
};

const STATUS_BADGE = {
  SHORTLISTED:      { bg: "bg-green-100", text: "text-green-700", icon: CheckCircle, label: "Shortlisted"  },
  REJECTED:         { bg: "bg-red-100",   text: "text-red-700",   icon: XCircle,     label: "Rejected"     },
  PENDING:          { bg: "bg-gray-100",  text: "text-gray-600",  icon: Clock,       label: "Pending"      },
  INTERVIEW_PENDING:{ bg: "bg-purple-100",text: "text-purple-700",icon: Clock,       label: "Interview"    },
  INTERVIEW_DONE:   { bg: "bg-blue-100",  text: "text-blue-700",  icon: CheckCircle, label: "Done"         },
};

function ScoreBar({ label, value, color = "blue" }) {
  const colorMap = { blue: "bg-blue-500", green: "bg-green-500", purple: "bg-purple-500" };
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="font-medium text-gray-700">{(value || 0).toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorMap[color]} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(value || 0, 100)}%` }}
        />
      </div>
    </div>
  );
}

// ── Candidate card ────────────────────────────────────────────
function CandidateCard({ candidate, matchResult, interviewSession, onStatusChange }) {
  const [expanded,        setExpanded]        = useState(false);
  const [updatingStatus,  setUpdatingStatus]  = useState(false);
  const [localStatus,     setLocalStatus]     = useState(candidate.status);

  const recStyle = matchResult?.recommendation
    ? REC_STYLE[matchResult.recommendation]
    : null;

  const missingSkills = (() => {
    const raw = matchResult?.missing_skills || candidate?.missing_skills || "";
    if (Array.isArray(raw)) return raw.filter(Boolean);
    return raw.split(",").map(s => s.trim()).filter(Boolean);
  })();

  const finalScore  = matchResult?.final_match_score ?? null;
  const statusStyle = STATUS_BADGE[localStatus] || STATUS_BADGE.PENDING;
  const StatusIcon  = statusStyle.icon;

  // ── Shortlist / Reject handler ──────────────────────────────
  const handleStatus = async (newStatus) => {
    if (localStatus === newStatus) return;
    setUpdatingStatus(true);
    try {
      await updateCandidateStatus(candidate.id, newStatus);
      setLocalStatus(newStatus);
      onStatusChange?.(candidate.id, newStatus);
      toast.success(
        newStatus === "SHORTLISTED"
          ? `${candidate.name} shortlisted ✓`
          : `${candidate.name} rejected`
      );
    } catch (err) {
      toast.error("Failed to update status: " + (err.userMessage || "Try again"));
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <div className={`card overflow-hidden border-l-4 transition-all ${
      localStatus === "SHORTLISTED" ? "border-l-green-400" :
      localStatus === "REJECTED"    ? "border-l-red-400"   :
                                       "border-l-gray-200"
    }`}>
      <div className="p-5">

        {/* Header: avatar + name + score */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
              localStatus === "SHORTLISTED" ? "bg-green-100" :
              localStatus === "REJECTED"    ? "bg-red-100"   :
                                              "bg-blue-100"
            }`}>
              <span className={`font-bold text-sm ${
                localStatus === "SHORTLISTED" ? "text-green-700" :
                localStatus === "REJECTED"    ? "text-red-700"   :
                                                "text-blue-700"
              }`}>
                {(candidate.name || "?").charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="font-semibold text-gray-900">{candidate.name}</p>
                {/* Current status badge */}
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
                  <StatusIcon size={10} />
                  {statusStyle.label}
                </span>
              </div>
              <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                <Mail size={11} /> {candidate.email}
              </p>
              {candidate.candidate_profile_id && (
                <p className="text-xs text-gray-400">
                  Profile #{candidate.candidate_profile_id}
                </p>
              )}
            </div>
          </div>

          {/* Score */}
          <div className="text-right shrink-0">
            <p className="text-2xl font-bold text-gray-900">
              {finalScore != null ? `${finalScore.toFixed(0)}%` : "—"}
            </p>
            <p className="text-xs text-gray-400">Match</p>
          </div>
        </div>

        {/* AI recommendation badge */}
        {recStyle && (
          <div className="mt-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${recStyle.bg} ${recStyle.text}`}>
              {recStyle.label}
            </span>
          </div>
        )}

        {/* No profile warning */}
        {!candidate.candidate_profile_id && (
          <div className="mt-3 flex items-center gap-2 text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
            <AlertTriangle size={12} />
            No portal profile linked — run screening first
          </div>
        )}

        {/* Skill match bar */}
        {matchResult && (
          <div className="mt-4">
            <ScoreBar label="Skill Match" value={matchResult.skill_match_score} color="green" />
          </div>
        )}

        {/* Missing skills */}
        {missingSkills.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 mb-1.5">Missing Skills</p>
            <div className="flex flex-wrap gap-1.5">
              {missingSkills.slice(0, 5).map((skill) => (
                <span key={skill} className="px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded-md">
                  {skill}
                </span>
              ))}
              {missingSkills.length > 5 && (
                <span className="px-2 py-0.5 bg-gray-100 text-gray-400 text-xs rounded-md">
                  +{missingSkills.length - 5} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Interview status */}
        {interviewSession && (
          <div className="mt-3 flex items-center gap-2 text-xs">
            <MessageSquare size={12} className="text-purple-500" />
            <span className="text-gray-500">Interview:</span>
            {interviewSession.interview_score != null ? (
              <span className="font-bold text-purple-600">
                {interviewSession.interview_score.toFixed(0)}%
              </span>
            ) : (
              <span className="text-gray-400">Pending answers</span>
            )}
            <span className={`px-2 py-0.5 rounded-full ${
              interviewSession.status === "EVALUATED"   ? "bg-purple-100 text-purple-700" :
              interviewSession.status === "COMPLETED"   ? "bg-blue-100 text-blue-700"     :
              interviewSession.status === "IN_PROGRESS" ? "bg-yellow-100 text-yellow-700" :
                                                          "bg-gray-100 text-gray-500"
            }`}>
              {interviewSession.status}
            </span>
          </div>
        )}

        {/* ── ACTION BUTTONS ── */}
        <div className="mt-4 pt-3 border-t border-gray-100 space-y-2">

          {/* Shortlist + Reject row */}
          <div className="flex gap-2">
            <button
              onClick={() => handleStatus("SHORTLISTED")}
              disabled={updatingStatus || localStatus === "SHORTLISTED"}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
                localStatus === "SHORTLISTED"
                  ? "bg-green-600 text-white cursor-default"
                  : "bg-green-50 text-green-700 border border-green-300 hover:bg-green-100"
              } disabled:opacity-60`}
            >
              <CheckCircle size={13} />
              {localStatus === "SHORTLISTED" ? "Shortlisted ✓" : "Shortlist"}
            </button>

            <button
              onClick={() => handleStatus("REJECTED")}
              disabled={updatingStatus || localStatus === "REJECTED"}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-lg transition-colors ${
                localStatus === "REJECTED"
                  ? "bg-red-600 text-white cursor-default"
                  : "bg-red-50 text-red-700 border border-red-300 hover:bg-red-100"
              } disabled:opacity-60`}
            >
              <XCircle size={13} />
              {localStatus === "REJECTED" ? "Rejected ✗" : "Reject"}
            </button>
          </div>

          {/* Secondary links row */}
          <div className="flex gap-2">
            <Link
              href={`/admin/analysis/${candidate.id}?jobId=${candidate.job_id}`}
              className="flex-1 text-center py-1.5 text-xs border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Brain size={11} className="inline mr-1" />
              Full Analysis
            </Link>

            {interviewSession?.id ? (
              <Link
                href={`/interview/results/${interviewSession.id}`}
                className="flex-1 text-center py-1.5 text-xs border border-purple-300 text-purple-600 rounded-lg hover:bg-purple-50 transition-colors"
              >
                <MessageSquare size={11} className="inline mr-1" />
                Interview Report
              </Link>
            ) : (
              <span className="flex-1 text-center py-1.5 text-xs border border-gray-200 text-gray-400 rounded-lg cursor-not-allowed">
                <MessageSquare size={11} className="inline mr-1" />
                No Interview Yet
              </span>
            )}

            {matchResult && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="px-3 py-1.5 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Expanded score breakdown */}
      {expanded && matchResult && (
        <div className="border-t border-gray-100 p-5 bg-gray-50 space-y-3">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Score Breakdown</p>
          <ScoreBar label="CV Semantic Similarity" value={matchResult.cv_similarity_score}  color="blue"   />
          <ScoreBar label="Skill Match"             value={matchResult.skill_match_score}    color="green"  />
          <ScoreBar label="Experience Match"        value={matchResult.experience_score}     color="purple" />
          {interviewSession?.interview_score != null && (
            <ScoreBar label="Interview Score" value={interviewSession.interview_score} color="purple" />
          )}
          {matchResult.ai_summary && (
            <p className="text-xs text-gray-500 italic pt-2 border-t border-gray-200">
              {matchResult.ai_summary}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────
export default function CandidatesPage() {
  const router         = useRouter();
  const { jobId }      = router.query;

  const [job,          setJob]          = useState(null);
  const [candidates,   setCandidates]   = useState([]);
  const [matchResults, setMatchResults] = useState([]);
  const [sessions,     setSessions]     = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [screening,    setScreening]    = useState(false);
  const [screenStep,   setScreenStep]   = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const STATUS_OPTIONS = ["ALL", "SHORTLISTED", "PENDING", "REJECTED"];

  useEffect(() => {
    if (!jobId) return;
    fetchAll();
  }, [jobId, statusFilter]);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [jobData, candidateData] = await Promise.all([
        getJob(jobId),
        getCandidatesForJob(jobId, statusFilter === "ALL" ? null : statusFilter),
      ]);
      setJob(jobData);
      setCandidates(candidateData);

      const [matches, interviewData] = await Promise.all([
        getJobMatchResults(jobId).catch(() => []),
        getJobInterviewSessions(jobId).catch(() => []),
      ]);
      setMatchResults(matches || []);
      setSessions(interviewData || []);
    } catch (err) {
      toast.error("Failed to load candidates");
    } finally {
      setLoading(false);
    }
  };

  // Update status locally without full reload
  const handleStatusChange = (candidateId, newStatus) => {
    setCandidates(prev =>
      prev.map(c => c.id === candidateId ? { ...c, status: newStatus } : c)
    );
  };

  // ── AI Screening pipeline ────────────────────────────────────
  const handleRunScreening = async () => {
    if (!candidates.length) {
      toast.error("No candidates to screen");
      return;
    }

    const profileCandidates = candidates.filter(c => c.candidate_profile_id);
    if (!profileCandidates.length) {
      toast.error("No candidates with portal profiles found. Ensure applications were submitted through the portal.");
      return;
    }

    setScreening(true);
    try {
      // Step 1: Process resumes — use candidate_profile_id (Phase 2)
      setScreenStep(`Processing ${profileCandidates.length} resume(s)...`);
      toast.loading("Step 1/4: Extracting resumes...", { id: "screen" });
      for (const c of profileCandidates) {
        try {
          await processResume(c.candidate_profile_id);
        } catch (e) {
          console.warn(`Resume skipped for profile ${c.candidate_profile_id}:`, e.userMessage || e.message);
        }
      }

      // Step 2: Generate candidate embeddings — use candidate_profile_id (Phase 2)
      setScreenStep("Generating candidate embeddings...");
      toast.loading("Step 2/4: Generating embeddings...", { id: "screen" });
      for (const c of profileCandidates) {
        try {
          await generateCandidateEmbedding(c.candidate_profile_id, false);
        } catch (e) {
          console.warn(`Embedding skipped for profile ${c.candidate_profile_id}:`, e.userMessage || e.message);
        }
      }

      // Step 3: Job embedding
      setScreenStep("Updating job embedding...");
      toast.loading("Step 3/4: Job embedding...", { id: "screen" });
      try {
        await generateJobEmbedding(jobId, false);
      } catch (e) {
        console.warn("Job embedding:", e.userMessage || e.message);
      }

      // Step 4: Bulk matching — internally calls auto_generate_interview per candidate
      setScreenStep("AI matching + generating interviews...");
      toast.loading("Step 4/4: Matching + interview generation...", { id: "screen" });
      await runBulkMatch(jobId, true);

      setScreenStep("Loading results...");
      await fetchAll();

      toast.success(
        `Screening complete for ${profileCandidates.length} candidate(s)!`,
        { id: "screen", duration: 5000 }
      );
    } catch (err) {
      toast.error(
        "Screening failed: " + (err.userMessage || err.message || "Unknown error"),
        { id: "screen" }
      );
    } finally {
      setScreening(false);
      setScreenStep("");
    }
  };

  // Lookup helpers — use candidate_profile_id for both
  const getMatchForCandidate = (c) =>
    matchResults.find(m => m.candidate_profile_id === c.candidate_profile_id) || null;

  const getSessionForCandidate = (c) =>
    sessions.find(s => s.candidate_profile_id === c.candidate_profile_id) || null;

  return (
    <Layout title={job ? `Candidates: ${job.title}` : "Candidates"}>

      <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft size={16} /> Back to Jobs
      </Link>

      {/* Job header */}
      {job && (
        <div className="card p-5 mb-6 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <Users size={20} className="text-blue-600" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">{job.title}</h2>
              <p className="text-sm text-gray-500">
                {job.department} · {candidates.length} candidate{candidates.length !== 1 ? "s" : ""}
                {matchResults.length > 0 && (
                  <span className="ml-2 text-green-600 font-medium">· {matchResults.length} screened</span>
                )}
                {sessions.length > 0 && (
                  <span className="ml-2 text-purple-600 font-medium">· {sessions.length} interview{sessions.length !== 1 ? "s" : ""}</span>
                )}
              </p>
            </div>
          </div>

          <button
            onClick={handleRunScreening}
            disabled={screening || candidates.length === 0}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={15} className={screening ? "animate-spin" : ""} />
            {screening ? (screenStep || "Screening...") : "Run AI Screening"}
          </button>
        </div>
      )}

      {/* Pipeline progress */}
      {screening && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-center gap-3">
          <RefreshCw size={16} className="text-blue-500 animate-spin shrink-0" />
          <div>
            <p className="text-sm font-semibold text-blue-800">{screenStep || "Running AI pipeline..."}</p>
            <p className="text-xs text-blue-600 mt-0.5">
              Extract CV → Embed → Semantic Match → Generate Interview Questions
            </p>
          </div>
        </div>
      )}

      {/* Status filter */}
      <div className="flex gap-1.5 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              statusFilter === s ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="flex gap-3 mb-4">
                <div className="w-10 h-10 bg-gray-200 rounded-full shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-32" />
                  <div className="h-3 bg-gray-200 rounded w-48" />
                </div>
              </div>
              <div className="h-2 bg-gray-200 rounded w-full mb-2" />
              <div className="h-8 bg-gray-200 rounded w-full mt-4" />
            </div>
          ))}
        </div>
      ) : candidates.length === 0 ? (
        <div className="text-center py-20">
          <Users size={32} className="text-gray-300 mx-auto mb-3" />
          <h3 className="font-medium text-gray-900">No candidates</h3>
          <p className="text-sm text-gray-400 mt-1">Candidates appear after applying through the portal.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              matchResult={getMatchForCandidate(candidate)}
              interviewSession={getSessionForCandidate(candidate)}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}