"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Layers, LogOut, TrendingUp } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export default function StudentSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isSessionsActive =
    pathname.startsWith("/student/session") || pathname === "/student/dashboard";
  const isMaterialsActive = pathname.startsWith("/student/material");
  const isProgressActive = pathname.startsWith("/student/progress");

  return (
    <aside className="w-64 bg-white border-r border-stone-200/60 flex flex-col justify-between fixed h-full z-20 top-0 left-0">
      <div>
        <div className="p-5 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#e65100]" />
          <h1 className="text-md font-bold tracking-tight text-stone-950">
            Learning Companion
          </h1>
        </div>

        <div className="px-3 mb-6">
          <div className="p-2.5 bg-white border border-stone-200/80 rounded-xl">
            <p className="text-[13px] font-bold text-stone-900 truncate pr-1">
              Real backend data
            </p>
            <p className="text-[10px] text-stone-400 font-medium">
              Real subjects only
            </p>
          </div>
        </div>

        <nav className="px-3 space-y-5">
          <div>
            <p className="px-2 text-[10px] font-bold text-stone-400 uppercase tracking-wider mb-1.5 text-left">
              Student
            </p>
            <div className="space-y-0.5">
              <Link
                href="/student/dashboard"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] font-bold rounded-lg transition-colors ${
                  isSessionsActive
                    ? "text-[#d84315] bg-[#fff3ed]"
                    : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <Layers size={15} />
                Sessions
              </Link>

              <Link
                href="/student/material"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] rounded-lg transition-colors ${
                  isMaterialsActive
                    ? "text-[#d84315] bg-[#fff3ed] font-bold"
                    : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <FileText size={15} />
                Materials
              </Link>

              <Link
                href="/student/progress"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] rounded-lg transition-colors ${
                  isProgressActive
                    ? "text-[#d84315] bg-[#fff3ed] font-bold"
                    : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <TrendingUp size={15} />
                My progress
              </Link>
            </div>
          </div>
        </nav>
      </div>

      <div className="p-4 border-t border-stone-100 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold text-stone-900 truncate">
            {user?.name ?? "Student"}
          </p>
          <p className="text-[10px] text-stone-400">Student</p>
        </div>
        <button
          type="button"
          onClick={logout}
          className="p-2 text-stone-400 hover:text-[#d84315] rounded-lg transition-colors"
          title="Log out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
