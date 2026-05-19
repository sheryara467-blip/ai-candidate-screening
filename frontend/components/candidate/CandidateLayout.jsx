// ============================================================
// components/candidate/CandidateLayout.jsx  —  NEW in Phase 2
// Public-facing layout for the candidate portal.
// Completely separate from the admin Layout.jsx (Phase 1).
// No sidebar — clean top-navbar design for job seekers.
// ============================================================

import Link from "next/link";
import { useRouter } from "next/router";
import { BriefcaseBusiness, ClipboardList, Home } from "lucide-react";

export default function CandidateLayout({ children, title = "Careers" }) {
  const router = useRouter();

  const navLinks = [
    { href: "/careers",             label: "Browse Jobs",       icon: BriefcaseBusiness },
    { href: "/applications/status", label: "My Applications",   icon: ClipboardList },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">

      {/* ======== NAVBAR ======== */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">

          {/* Brand */}
          <Link href="/careers" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <BriefcaseBusiness size={16} className="text-white" />
            </div>
            <span className="font-bold text-gray-900 text-sm">
              AI Screening <span className="text-blue-600">Careers</span>
            </span>
          </Link>

          {/* Nav links */}
          <nav className="flex items-center gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = router.pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  <Icon size={15} />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {/* ======== PAGE CONTENT ======== */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
        {children}
      </main>

      {/* ======== FOOTER ======== */}
      <footer className="border-t border-gray-200 bg-white py-6 text-center text-xs text-gray-400">
        AI Candidate Screening System · Phase 2 · Candidate Portal
      </footer>

    </div>
  );
}