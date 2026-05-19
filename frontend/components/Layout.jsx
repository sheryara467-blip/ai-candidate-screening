// ============================================================
// components/Layout.jsx
// Main admin dashboard layout with sidebar navigation.
// Wrap every admin page with this component.
// ============================================================

import Link from "next/link";
import { useRouter } from "next/router";
import {
  LayoutDashboard,
  BriefcaseBusiness,
  PlusCircle,
  Users,
  RefreshCw,
  ChevronRight,
} from "lucide-react";

// Sidebar navigation items
const navItems = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Jobs",
    href: "/jobs",
    icon: BriefcaseBusiness,
  },
  {
    label: "Post New Job",
    href: "/jobs/create",
    icon: PlusCircle,
  },
];

export default function Layout({ children, title = "Admin Dashboard" }) {
  const router = useRouter();

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">

      {/* ======== SIDEBAR ======== */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col shrink-0">
        {/* Logo / Brand */}
        <div className="px-6 py-5 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Users size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-white">AI Screening</p>
              <p className="text-xs text-gray-400">Admin Panel</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? router.pathname === "/"
                : router.pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <Icon size={18} />
                {item.label}
                {isActive && <ChevronRight size={14} className="ml-auto" />}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-700">
          <p className="text-xs text-gray-500">Phase 1 — Admin Dashboard</p>
          <p className="text-xs text-gray-600 mt-0.5">v1.0.0</p>
        </div>
      </aside>

      {/* ======== MAIN CONTENT ======== */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top navbar */}
        <header className="bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between shrink-0">
          <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">A</span>
            </div>
            <span className="text-sm text-gray-600">Admin</span>
          </div>
        </header>

        {/* Page content — scrollable */}
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}