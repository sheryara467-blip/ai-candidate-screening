// ============================================================
// EXACT FILE LOCATION: frontend/pages/applications/status.js
// ============================================================
// PURPOSE: Candidate status tracking page.
// Candidate enters their email to see all their applications
// and the current status of each one.
//
// Workflow:
//   1. Candidate lands on this page
//   2. Types their email address
//   3. Clicks "Check Status"
//   4. Page fetches GET /portal/applications/{email}
//   5. Shows a card for each application with status badge
//
// Also works with ?email=xxx query param (auto-fills after apply)
//
// UPDATED:
//   - Shows "Start Interview" button when session is ready
//   - Polls every 30s after submission so interview button
//     appears automatically once pipeline completes
// ============================================================

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import CandidateLayout from "../../components/candidate/CandidateLayout";
import ApplicationStatusBadge, { StatusBadge } from "../../components/candidate/ApplicationStatusBadge";
import { getMyApplications } from "../../services/api";
import toast from "react-hot-toast";
import {
  Search,
  BriefcaseBusiness,
  Calendar,
  Building2,
  ArrowRight,
  Inbox,
  MessageSquare,
  Loader,
  RefreshCw,
} from "lucide-react";

export default function ApplicationStatusPage() {
  const router = useRouter();

  const [email,        setEmail]        = useState("");
  const [applications, setApplications] = useState([]);
  const [loading,      setLoading]      = useState(false);
  const [searched,     setSearched]     = useState(false);
  const [error,        setError]        = useState("");
  const [polling,      setPolling]      = useState(false);

  // ============================================================
  // If user came from /apply page, email is in the query string
  // Auto-fill and auto-search so they land straight on results
  // ============================================================
  useEffect(() => {
    if (router.query.email) {
      const emailFromQuery = decodeURIComponent(router.query.email);
      setEmail(emailFromQuery);
      fetchApplications(emailFromQuery);
    }
  }, [router.query.email]);

  // ============================================================
  // Poll every 30s if any application has no interview yet
  // Stops when all have interview_session_id or user navigates away
  // ============================================================
  useEffect(() => {
    if (!searched || !email) return;

    const hasPending = applications.some(
      (a) => !a.interview_session_id
    );

    if (!hasPending) return;

    const timer = setInterval(() => {
      setPolling(true);

      fetchApplications(email, true)
        .finally(() => setPolling(false));
    }, 30000);

    return () => clearInterval(timer);
  }, [searched, applications, email]);

  // ============================================================
  // Fetch applications for the entered email from backend
  // ============================================================
  const fetchApplications = useCallback(async (emailToSearch, silent = false) => {
    const target = (emailToSearch || email).trim().toLowerCase();

    // Basic email validation
    if (!target) {
      if (!silent) {
        setError("Please enter your email address");
      }
      return;
    }

    if (!/\S+@\S+\.\S+/.test(target)) {
      if (!silent) {
        setError("Please enter a valid email address");
      }
      return;
    }

    setError("");

    if (!silent) {
      setLoading(true);
    }

    try {
      // Call GET /portal/applications/{email}
      const data = await getMyApplications(target);

      setApplications(data);
      setSearched(true);
    } catch (err) {
      if (!silent) {
        toast.error("Failed to fetch applications. Please try again.");
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [email]);

  // Handle form submit
  const handleSubmit = (e) => {
    e.preventDefault();
    fetchApplications();
  };

  // Format date nicely
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year:  "numeric",
      month: "long",
      day:   "numeric",
    });
  };

  // ============================================================
  // Interview status helper
  // ============================================================
  const interviewLabel = (app) => {
    if (app.interview_session_id) {
      return {
        ready: true,
        text: "Interview Ready",
      };
    }

    if (app.status === "SUBMITTED") {
      return {
        ready: false,
        text: "Processing...",
      };
    }

    return {
      ready: false,
      text: "Pending",
    };
  };

  return (
    <CandidateLayout title="My Applications">

      {/* ======== PAGE HEADER ======== */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-extrabold text-gray-900 mb-2">
          Track Your Applications
        </h1>

        <p className="text-gray-500">
          Enter the email address you used when applying to see your status.
        </p>
      </div>

      {/* ======== EMAIL SEARCH FORM ======== */}
      <form
        onSubmit={handleSubmit}
        className="max-w-lg mx-auto mb-10"
      >
        <div className="flex gap-2">

          {/* Email input */}
          <div className="flex-1 relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
            />

            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError("");
              }}
              placeholder="Enter your email address"
              className={`w-full pl-9 pr-4 py-3 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition ${
                error
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300"
              }`}
            />
          </div>

          {/* Search button */}
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-3 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              "Check Status"
            )}
          </button>
        </div>

        {/* Validation error */}
        {error && (
          <p className="text-red-500 text-xs mt-2 ml-1">
            {error}
          </p>
        )}
      </form>

      {/* ======== RESULTS SECTION ======== */}

      {/* Loading skeleton */}
      {loading && (
        <div className="max-w-2xl mx-auto space-y-4">
          {[...Array(2)].map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse"
            >
              <div className="h-5 bg-gray-200 rounded w-2/3 mb-3" />
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="h-8 bg-gray-200 rounded w-36" />
            </div>
          ))}
        </div>
      )}

      {/* No applications found */}
      {!loading && searched && applications.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Inbox size={24} className="text-gray-400" />
          </div>

          <h3 className="font-semibold text-gray-900 mb-1">
            No applications found
          </h3>

          <p className="text-gray-400 text-sm mb-6">
            We couldn't find any applications for{" "}
            <span className="font-medium text-gray-600">
              {email}
            </span>
          </p>

          <Link
            href="/careers"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors"
          >
            <BriefcaseBusiness size={15} />
            Browse Open Jobs
          </Link>
        </div>
      )}

      {/* Applications list */}
      {!loading && applications.length > 0 && (
        <div className="max-w-2xl mx-auto">

          {/* Result count + polling */}
          <div className="flex items-center justify-between mb-4">

            <p className="text-sm text-gray-400">
              Found{" "}
              <span className="font-semibold text-gray-700">
                {applications.length}
              </span>{" "}
              application{applications.length !== 1 ? "s" : ""} for{" "}
              <span className="font-medium text-gray-700">
                {email}
              </span>
            </p>

            <div className="flex items-center gap-4">

              {polling && (
                <span className="flex items-center gap-1.5 text-xs text-blue-500">
                  <Loader
                    size={12}
                    className="animate-spin"
                  />
                  Checking for updates...
                </span>
              )}

              <button
                onClick={() => fetchApplications(email)}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
              >
                <RefreshCw size={12} />
                Refresh
              </button>

            </div>
          </div>

          {/* Application cards */}
          <div className="space-y-4">
            {applications.map((app) => {
              const iv = interviewLabel(app);

              return (
                <div
                  key={app.application_id}
                  className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-sm transition-shadow"
                >

                  {/* Job title + department */}
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <h3 className="font-bold text-gray-900 text-lg">
                        {app.job_title}
                      </h3>

                      <p className="text-sm text-gray-500 flex items-center gap-1.5 mt-0.5">
                        <Building2 size={13} />
                        {app.department}
                      </p>
                    </div>

                    {/* Inline status badge */}
                    <StatusBadge status={app.status} />
                  </div>

                  {/* Status detail card */}
                  <div className="mb-4">
                    <ApplicationStatusBadge status={app.status} />
                  </div>

                  {/* ============================================================
                      NEW: Interview section
                  ============================================================ */}
                  <div
                    className={`rounded-xl border p-4 mb-4 flex items-center justify-between gap-4 ${
                      iv.ready
                        ? "bg-purple-50 border-purple-200"
                        : "bg-gray-50 border-gray-200"
                    }`}
                  >

                    <div className="flex items-center gap-3">
                      <MessageSquare
                        size={18}
                        className={
                          iv.ready
                            ? "text-purple-600"
                            : "text-gray-400"
                        }
                      />

                      <div>
                        <p
                          className={`text-sm font-semibold ${
                            iv.ready
                              ? "text-purple-800"
                              : "text-gray-500"
                          }`}
                        >
                          AI Interview
                        </p>

                        <p className="text-xs text-gray-400 mt-0.5">
                          {iv.ready
                            ? "Your interview questions are ready. Answer at your own pace."
                            : "AI is processing your CV. Interview will appear here automatically."}
                        </p>
                      </div>
                    </div>

                    {iv.ready ? (
                      <Link
                        href={`/interview/${app.interview_session_id}`}
                        className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white text-sm font-semibold rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        Start Interview
                        <ArrowRight size={14} />
                      </Link>
                    ) : (
                      <span className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-gray-200 text-gray-400 text-sm rounded-lg cursor-not-allowed">
                        <Loader
                          size={13}
                          className="animate-spin"
                        />
                        {iv.text}
                      </span>
                    )}
                  </div>

                  {/* Applied date + application ID */}
                  <div className="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-100">
                    <span className="flex items-center gap-1.5">
                      <Calendar size={12} />
                      Applied on {formatDate(app.applied_on)}
                    </span>

                    <span className="font-mono">
                      ID #{app.application_id}
                    </span>
                  </div>

                </div>
              );
            })}
          </div>

          {/* Browse more jobs link */}
          <div className="mt-8 text-center">
            <Link
              href="/careers"
              className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Browse more open positions
              <ArrowRight size={14} />
            </Link>
          </div>

        </div>
      )}

    </CandidateLayout>
  );
}