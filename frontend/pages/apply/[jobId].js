// ============================================================
// pages/apply/[jobId].js  —  NEW in Phase 2
// Application form page for a specific job.
//
// Two-step workflow:
//   Step 1 — Upload CV (POST /portal/upload-cv)
//             Returns resume_path to embed in form payload
//   Step 2 — Submit form (POST /portal/apply)
//             Saves CandidateProfile + Application to SQLite
//
// After success: shows confirmation card with application ID.
// ============================================================

import { useEffect, useState } from "react";
import { useRouter }  from "next/router";
import Link           from "next/link";
import CandidateLayout from "../../components/candidate/CandidateLayout";
import { getPublicJob, uploadCV, submitApplication, getMyApplications } from "../../services/api";
import ApplicationStatusBadge from "../../components/candidate/ApplicationStatusBadge";
import toast from "react-hot-toast";
import {
  ArrowLeft, Upload, CheckCircle, FileText, Send, AlertCircle
} from "lucide-react";

const EMPTY_FORM = {
  full_name:     "",
  email:         "",
  phone:         "",
  cover_message: "",
};

export default function ApplyPage() {
  const router    = useRouter();
  const { jobId } = router.query;

  const [job,          setJob]          = useState(null);
  const [form,         setForm]         = useState(EMPTY_FORM);
  const [cvFile,       setCvFile]       = useState(null);
  const [resumePath,   setResumePath]   = useState("");
  const [uploading,    setUploading]    = useState(false);
  const [submitting,   setSubmitting]   = useState(false);
  const [submitted,    setSubmitted]    = useState(false);
  const [applicationId, setApplicationId] = useState(null);
  const [interviewSessionId, setInterviewSessionId] = useState(null); // set by polling
  const [errors,       setErrors]       = useState({});

  // Fetch job info to display at top of form
  useEffect(() => {
    if (!jobId) return;
    getPublicJob(jobId).then(setJob).catch(() => {});
  }, [jobId]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: null }));
  };

  // ============================================================
  // Step 1: Handle CV file selection and immediate upload
  // Upload happens as soon as user picks the file so we have
  // resume_path ready when they hit Submit.
  // ============================================================
  const handleCVSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side validation: PDF only
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Please select a PDF file");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error("File is too large. Maximum size is 5 MB.");
      return;
    }

    setCvFile(file);
    setUploading(true);

    try {
      // Upload the CV to backend — returns { resume_path, filename }
      const result = await uploadCV(file);
      setResumePath(result.resume_path);
      toast.success("CV uploaded successfully");
    } catch (err) {
      toast.error("CV upload failed: " + (err.userMessage || "Please try again"));
      setCvFile(null);
    } finally {
      setUploading(false);
    }
  };

  // Form validation before submission
  const validate = () => {
    const errs = {};
    if (!form.full_name.trim()) errs.full_name = "Full name is required";
    if (!form.email.trim())     errs.email     = "Email is required";
    if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = "Enter a valid email address";
    if (!resumePath)            errs.cv        = "Please upload your CV";
    return errs;
  };

  // ============================================================
  // Step 2: Submit full application form to backend
  // ============================================================
  const handleSubmit = async (e) => {
    e.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      toast.error("Please fix the form errors");
      return;
    }

    setSubmitting(true);
    try {
      // Submit application — backend creates CandidateProfile + Application
      const result = await submitApplication({
        ...form,
        job_id:      parseInt(jobId),
        resume_path: resumePath,
      });

      setApplicationId(result.id);
      setSubmitted(true);
      toast.success("Application submitted!");

      // ── FIX 3: Poll for interview session ──────────────────
      // The background pipeline takes ~30-60s to complete.
      // Poll every 5s up to 20 attempts (100s total).
      // When interview_session_id appears, redirect candidate.
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const apps = await getMyApplications(form.email);
          const thisApp = apps.find(a => a.job_id === parseInt(jobId));
          if (thisApp?.interview_session_id) {
            clearInterval(pollInterval);
            setInterviewSessionId(thisApp.interview_session_id);
          }
        } catch {
          // Non-fatal — keep polling
        }
        if (attempts >= 20) {
          clearInterval(pollInterval); // stop after 100s
        }
      }, 5000);

    } catch (err) {
      const msg = err.userMessage || "Submission failed. Please try again.";
      if (msg.includes("already applied")) {
        toast.error("You have already applied for this job.");
      } else {
        toast.error(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ============================================================
  // CONFIRMATION SCREEN — shown after successful submission
  // ============================================================
  if (submitted) {
    return (
      <CandidateLayout title="Application Submitted">
        <div className="max-w-lg mx-auto text-center py-10">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <CheckCircle size={36} className="text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Application Submitted!
          </h1>
          <p className="text-gray-500 mb-1">
            Thank you, <span className="font-semibold text-gray-700">{form.full_name}</span>.
          </p>
          <p className="text-gray-500 mb-6">
            Your application for <span className="font-semibold text-gray-700">{job?.title}</span> has been received.
          </p>

          {/* Status badge */}
          <div className="text-left mb-6">
            <ApplicationStatusBadge status="SUBMITTED" />
          </div>

          {/* Application ID */}
          {applicationId && (
            <p className="text-xs text-gray-400 mb-8">
              Application ID: <span className="font-mono font-medium text-gray-600">#{applicationId}</span>
            </p>
          )}

          {/* AI Pipeline status + Interview button */}
          <div className={`rounded-xl border p-4 mb-6 text-left ${
            interviewSessionId
              ? "bg-purple-50 border-purple-200"
              : "bg-blue-50 border-blue-200"
          }`}>
            {interviewSessionId ? (
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-purple-800">
                    🎉 Interview Ready!
                  </p>
                  <p className="text-xs text-purple-600 mt-0.5">
                    Your AI interview questions have been generated.
                  </p>
                </div>
                <Link
                  href={`/interview/${interviewSessionId}`}
                  className="shrink-0 px-4 py-2 bg-purple-600 text-white text-sm font-semibold rounded-lg hover:bg-purple-700 transition-colors"
                >
                  Start Interview →
                </Link>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-blue-800">
                    AI is processing your application...
                  </p>
                  <p className="text-xs text-blue-600 mt-0.5">
                    Extracting CV → Generating embeddings → Matching → Creating interview questions
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Next steps */}
          <div className="flex flex-col gap-3">
            <Link
              href={`/applications/status?email=${encodeURIComponent(form.email)}`}
              className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors text-sm"
            >
              Track My Application
            </Link>
            <Link href="/careers" className="w-full py-3 border border-gray-300 text-gray-600 font-medium rounded-xl hover:bg-gray-50 transition-colors text-sm">
              Browse More Jobs
            </Link>
          </div>
        </div>
      </CandidateLayout>
    );
  }

  // ============================================================
  // APPLICATION FORM
  // ============================================================
  return (
    <CandidateLayout title="Apply">

      {/* Back link */}
      <Link
        href={jobId ? `/careers/${jobId}` : "/careers"}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft size={15} /> Back to job details
      </Link>

      {/* Job context banner */}
      {job && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl px-5 py-4 mb-7 flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
            <FileText size={16} className="text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm">{job.title}</p>
            <p className="text-xs text-gray-500">{job.department}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="max-w-xl space-y-7">

        {/* ======== PERSONAL DETAILS ======== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-5 pb-3 border-b border-gray-100">
            Personal Details
          </h2>
          <div className="space-y-4">

            {/* Full name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Name *
              </label>
              <input
                type="text"
                name="full_name"
                value={form.full_name}
                onChange={handleChange}
                placeholder="e.g. Ali Hassan"
                className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition ${errors.full_name ? "border-red-400" : "border-gray-300"}`}
              />
              {errors.full_name && <p className="text-red-500 text-xs mt-1">{errors.full_name}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address *
              </label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="ali@example.com"
                className={`w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition ${errors.email ? "border-red-400" : "border-gray-300"}`}
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
              <p className="text-xs text-gray-400 mt-1">
                Use this email to track your application status later.
              </p>
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                name="phone"
                value={form.phone}
                onChange={handleChange}
                placeholder="+92-300-1234567"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              />
            </div>

          </div>
        </div>

        {/* ======== CV UPLOAD ======== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-1">Upload CV / Resume *</h2>
          <p className="text-xs text-gray-400 mb-4">PDF format only · Max 5 MB</p>

          <label className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl py-8 cursor-pointer transition-colors ${
            errors.cv
              ? "border-red-400 bg-red-50"
              : cvFile
              ? "border-green-400 bg-green-50"
              : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"
          }`}>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleCVSelect}
              className="hidden"
              disabled={uploading}
            />

            {uploading ? (
              <>
                <span className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-blue-600 font-medium">Uploading...</span>
              </>
            ) : cvFile ? (
              <>
                <CheckCircle size={28} className="text-green-500" />
                <span className="text-sm font-semibold text-green-700">{cvFile.name}</span>
                <span className="text-xs text-gray-400">Click to replace</span>
              </>
            ) : (
              <>
                <Upload size={28} className="text-gray-400" />
                <span className="text-sm font-medium text-gray-600">
                  Click to select your PDF resume
                </span>
                <span className="text-xs text-gray-400">or drag and drop here</span>
              </>
            )}
          </label>
          {errors.cv && (
            <p className="text-red-500 text-xs mt-2 flex items-center gap-1">
              <AlertCircle size={12} /> {errors.cv}
            </p>
          )}
        </div>

        {/* ======== COVER MESSAGE ======== */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-1">Cover Message</h2>
          <p className="text-xs text-gray-400 mb-4">Optional — briefly introduce yourself</p>
          <textarea
            name="cover_message"
            value={form.cover_message}
            onChange={handleChange}
            rows={4}
            placeholder="Tell us why you're a great fit for this role..."
            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none transition"
          />
        </div>

        {/* ======== SUBMIT ======== */}
        <button
          type="submit"
          disabled={submitting || uploading}
          className="w-full flex items-center justify-center gap-2 py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              <Send size={16} />
              Submit Application
            </>
          )}
        </button>

      </form>
    </CandidateLayout>
  );
}