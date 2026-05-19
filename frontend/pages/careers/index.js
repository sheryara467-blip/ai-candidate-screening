// ============================================================
// pages/careers/index.js  —  NEW in Phase 2
// Public careers page — lists all OPEN jobs.
// Candidate lands here to browse and choose a job to apply for.
// ============================================================

import { useEffect, useState } from "react";
import CandidateLayout from "../../components/candidate/CandidateLayout";
import JobListingCard  from "../../components/candidate/JobListingCard";
import { getOpenJobs }  from "../../services/api";
import { BriefcaseBusiness, Search } from "lucide-react";

export default function CareersPage() {
  const [jobs,    setJobs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [search,  setSearch]  = useState("");

  // Fetch all open jobs from the portal API on mount
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const data = await getOpenJobs();
        setJobs(data);
      } catch (err) {
        console.error("Failed to load jobs:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
  }, []);

  // Client-side filter by search term (title or department)
  const filtered = jobs.filter((job) => {
    const term = search.toLowerCase();
    return (
      job.title.toLowerCase().includes(term) ||
      job.department.toLowerCase().includes(term) ||
      (job.required_skills || "").toLowerCase().includes(term)
    );
  });

  return (
    <CandidateLayout title="Browse Jobs">

      {/* ======== HERO ======== */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-3">
          Find Your Next Role
        </h1>
        <p className="text-gray-500 text-lg">
          Browse open positions and apply with your CV in minutes.
        </p>
      </div>

      {/* ======== SEARCH BAR ======== */}
      <div className="relative max-w-xl mx-auto mb-10">
        <Search
          size={18}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
        />
        <input
          type="text"
          placeholder="Search by title, department, or skill..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
        />
      </div>

      {/* ======== RESULTS COUNT ======== */}
      {!loading && (
        <p className="text-sm text-gray-400 mb-5">
          {filtered.length} open position{filtered.length !== 1 ? "s" : ""}
          {search && ` for "${search}"`}
        </p>
      )}

      {/* ======== JOB GRID ======== */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-2/3 mb-3" />
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="h-3 bg-gray-200 rounded w-full mb-2" />
              <div className="h-3 bg-gray-200 rounded w-4/5 mb-4" />
              <div className="flex gap-2">
                <div className="h-7 bg-gray-200 rounded w-16" />
                <div className="h-7 bg-gray-200 rounded w-16" />
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-24">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <BriefcaseBusiness size={24} className="text-gray-400" />
          </div>
          <h3 className="font-semibold text-gray-900">No open positions found</h3>
          <p className="text-gray-400 text-sm mt-1">
            {search ? "Try a different search term." : "Check back soon for new openings."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map((job) => (
            <JobListingCard key={job.id} job={job} />
          ))}
        </div>
      )}

    </CandidateLayout>
  );
}