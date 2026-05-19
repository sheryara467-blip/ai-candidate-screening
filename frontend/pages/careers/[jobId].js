// ============================================================
// pages/careers/[jobId].js  —  NEW in Phase 2
// Job detail page — shows full job info for a specific job.
// Candidate reads this before deciding to apply.
// ============================================================

import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import CandidateLayout from "../../components/candidate/CandidateLayout";
import { getPublicJob } from "../../services/api";
import {
  ArrowLeft, ArrowRight, Clock, GraduationCap,
  Building2, Lightbulb, CheckCircle,
} from "lucide-react";

export default function JobDetailPage() {
  const router       = useRouter();
  const { jobId }    = router.query;
  const [job,    setJob]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    if (!jobId) return;
    const fetchJob = async () => {
      try {
        const data = await getPublicJob(jobId);
        setJob(data);
      } catch (err) {
        setError("This job could not be found.");
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [jobId]);

  // Parse skills string into array
  const skills = job?.required_skills
    ? job.required_skills.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  if (loading) {
    return (
      <CandidateLayout>
        <div className="max-w-2xl mx-auto animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-1/3" />
          <div className="h-32 bg-gray-200 rounded" />
        </div>
      </CandidateLayout>
    );
  }

  if (error || !job) {
    return (
      <CandidateLayout>
        <div className="text-center py-20">
          <p className="text-red-500 font-medium">{error || "Job not found"}</p>
          <Link href="/careers" className="mt-4 inline-flex items-center gap-1.5 text-blue-600 text-sm">
            <ArrowLeft size={14} /> Back to Jobs
          </Link>
        </div>
      </CandidateLayout>
    );
  }

  return (
    <CandidateLayout title={job.title}>

      {/* Back link */}
      <Link href="/careers" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft size={15} /> Back to all jobs
      </Link>

      <div className="max-w-2xl">

        {/* ======== JOB HEADER ======== */}
        <div className="bg-white rounded-xl border border-gray-200 p-7 mb-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
              <p className="text-gray-500 font-medium mt-1 flex items-center gap-1.5">
                <Building2 size={14} /> {job.department}
              </p>
            </div>
            <span className="shrink-0 px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">
              Open
            </span>
          </div>

          {/* Meta: experience + education */}
          <div className="flex flex-wrap gap-5 text-sm text-gray-500 pb-5 border-b border-gray-100 mb-5">
            {job.experience && (
              <span className="flex items-center gap-1.5">
                <Clock size={14} className="text-blue-500" />
                {job.experience}
              </span>
            )}
            {job.education && (
              <span className="flex items-center gap-1.5">
                <GraduationCap size={14} className="text-blue-500" />
                {job.education}
              </span>
            )}
          </div>

          {/* Description */}
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">
              About This Role
            </h2>
            <p className="text-gray-600 text-sm leading-7 whitespace-pre-line">
              {job.description}
            </p>
          </div>

          {/* Required skills */}
          {skills.length > 0 && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                <Lightbulb size={14} /> Required Skills
              </h2>
              <div className="flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="flex items-center gap-1 px-3 py-1.5 bg-blue-50 text-blue-700 text-xs font-medium rounded-lg"
                  >
                    <CheckCircle size={11} />
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Requirements list */}
          {job.requirements && job.requirements.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                Job Requirements
              </h2>
              <ul className="space-y-2">
                {job.requirements.map((req) => (
                  <li key={req.id} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className={`mt-0.5 w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${req.is_mandatory ? "bg-red-400" : "bg-gray-300"}`} />
                    <span>
                      <span className="font-medium text-gray-700">{req.category}: </span>
                      {req.description}
                      {!req.is_mandatory && <span className="text-gray-400 ml-1">(preferred)</span>}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* ======== APPLY CTA ======== */}
        <div className="flex gap-3">
          <Link
            href={`/apply/${job.id}`}
            className="flex-1 flex items-center justify-center gap-2 py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors"
          >
            Apply for This Position
            <ArrowRight size={16} />
          </Link>
          <Link href="/careers" className="px-5 py-3.5 border border-gray-300 text-gray-600 font-medium rounded-xl hover:bg-gray-50 transition-colors text-sm">
            Back
          </Link>
        </div>

      </div>
    </CandidateLayout>
  );
}