"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  TrendingUp,
  FileText,
  LogOut,
  Search,
  Plus,
  Calendar,
  Clock,
  CheckCircle2,
  Camera,
  ChevronDown,
  X,
} from "lucide-react";

import {
  getStudentDashboardViewModel,
  type AppSubject,
  type StudentDashboardViewModel,
} from "@/lib/api";
import StudentSidebar from "@/components/studentsidebar";

function formatAttendanceTime(value: string) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Studentsidebar() {
  const [viewModel, setViewModel] = useState<StudentDashboardViewModel>({
    subjects: [],
    sessionsBySubject: {},
    attendance: {
      presentCount: 0,
      totalActiveSessions: 0,
    },
  });
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<AppSubject>({
      id: "",
      code: "",
      name: "",
      displayShort: "",
      weeks: "",
  });
  const [searchQuery, setSearchQuery] = useState("");

  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [subjectCode, setSubjectCode] = useState("");

  useEffect(() => {
    let ignore = false;

    getStudentDashboardViewModel()
      .then((nextViewModel) => {
        if (ignore) return;
        setViewModel(nextViewModel);
        setSelectedSubject(
          nextViewModel.subjects[0] ?? {
            id: "",
            code: "",
            name: "",
            displayShort: "",
            weeks: "",
          },
        );
      })
      .catch((error) => {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load sessions.",
          );
        }
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, []);

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  };

  const handleAddSubjectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`Adding subject with code: ${subjectCode}`);
    setIsAddSubjectModalOpen(false);
    setSubjectCode("");
  };

  const currentSessions = viewModel.sessionsBySubject[selectedSubject.code] ?? [];

  const filteredSessions = currentSessions.filter((session) => {
    const query = searchQuery.toLowerCase().trim();
    return (
      session.title.toLowerCase().includes(query) ||
      session.description.toLowerCase().includes(query) ||
      session.week.toLowerCase().includes(query)
    );
  });

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <StudentSidebar />

      {/* RIGHT MAIN CONTENT */}
      <main
        suppressHydrationWarning
        className="flex-1 pl-64 px-8 pt-14 pb-8 relative overflow-hidden text-left"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          {/* Header Area */}
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
                Your sessions
              </h2>
              <p className="text-xs text-stone-400 mt-1">
                {selectedSubject.code} - {selectedSubject.name} - prepare before
                class, catch up if you missed something.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative w-64">
                <Search
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
                />
                <input
                  suppressHydrationWarning
                  type="text"
                  placeholder="Search sessions"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 h-9 bg-white border border-stone-200/80 rounded-full text-xs placeholder:text-stone-300 outline-none focus:border-orange-500/50"
                />
              </div>
            </div>
          </div>

          {isLoading && (
            <div className="text-center py-12 bg-white rounded-xl border border-stone-200/50">
              <p className="text-sm text-stone-400 font-medium">
                Loading real sessions...
              </p>
            </div>
          )}

          {!isLoading && loadError && (
            <div className="text-center py-12 bg-white rounded-xl border border-red-100">
              <p className="text-sm text-red-500 font-medium">{loadError}</p>
            </div>
          )}

          {!isLoading && !loadError && (
            <section className="bg-white border border-stone-200/70 rounded-xl p-5 shadow-sm">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-400">
                    Attendance
                  </p>
                  <h3 className="mt-1 text-lg font-bold text-stone-900">
                    {viewModel.attendance.presentCount} / {viewModel.attendance.totalActiveSessions} active sessions checked in
                  </h3>
                  <p className="mt-1 text-xs text-stone-400">
                    Photo check-in is recorded without AI verification.
                  </p>
                </div>
                <div className="flex items-center gap-3 rounded-xl bg-orange-50 px-4 py-3 text-[#d84315]">
                  <Camera size={18} />
                  <span className="text-xs font-bold">
                    {viewModel.attendance.latest
                      ? `Latest: ${formatAttendanceTime(viewModel.attendance.latest.checkedInAt)}`
                      : "No check-ins yet"}
                  </span>
                </div>
              </div>
            </section>
          )}

          {/* Cards Grid */}
          {!isLoading && !loadError && filteredSessions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSessions.map((session) => {
                const isActive = session.status === "Active";

                return (
                  <div
                    key={session.id}
                    onClick={() => {
                      if (isActive && typeof window !== "undefined") {
                        window.location.assign(
                          `/student/session/${session.id}`,
                        );
                      }
                    }}
                    className={`bg-white border border-stone-200/60 rounded-xl p-5 flex flex-col justify-between min-h-[170px] shadow-sm transition-all ${
                      isActive
                        ? "cursor-pointer hover:shadow-md hover:border-orange-300"
                        : "cursor-default"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider">
                          {session.week}
                        </span>

                        {session.status === "Completed" && (
                          <span className="px-2.5 py-0.5 bg-green-50 text-green-600 rounded-full text-[10px] font-semibold border border-green-100">
                            Completed
                          </span>
                        )}
                        {session.status === "Active" && (
                          <span className="px-2.5 py-0.5 bg-[#fff3ed] text-[#d84315] rounded-full text-[10px] font-bold border border-orange-100">
                            Active
                          </span>
                        )}
                        {session.status === "Upcoming" && (
                          <span className="px-2.5 py-0.5 bg-white text-stone-400 border border-stone-200 rounded-full text-[10px] font-semibold">
                            Upcoming
                          </span>
                        )}
                      </div>
                      {session.attendance?.isPresent && (
                        <div className="mb-2 inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-600 ring-1 ring-emerald-100">
                          <CheckCircle2 size={12} />
                          Checked in
                        </div>
                      )}

                      <h3 className="text-base font-bold text-stone-900 leading-snug mb-1">
                        {session.title}
                      </h3>
                      <p className="text-xs text-stone-400 line-clamp-2 leading-relaxed">
                        {session.description}
                      </p>
                    </div>

                    <div className="mt-4 pt-4 border-t border-stone-100 flex items-center gap-4 text-[11px] text-stone-400 font-medium">
                      <div className="flex items-center gap-1">
                        <Calendar size={13} className="text-stone-300" />
                        <span>{session.date}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock size={13} className="text-stone-300" />
                        <span
                          className={
                            session.status === "Active"
                              ? "text-stone-500 font-semibold"
                              : ""
                          }
                        >
                          {session.info}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : !isLoading && !loadError ? (
            <div className="text-center py-12 bg-white rounded-xl border border-stone-200/50">
              <p className="text-sm text-stone-400 font-medium">
                No real sessions found{searchQuery ? ` matching "${searchQuery}"` : ""}.
              </p>
            </div>
          ) : null}
        </div>
      </main>

      {isAddSubjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[1px] p-4 transition-all">
          <div className="bg-white rounded-[26px] max-w-[460px] w-full p-7 relative shadow-2xl border border-stone-100 text-left animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-[20px] font-bold text-stone-950 tracking-tight">
                Add a subject
              </h3>
              <button
                onClick={() => {
                  setIsAddSubjectModalOpen(false);
                  setSubjectCode("");
                }}
                className="text-stone-400 hover:text-stone-600 transition-colors p-1 rounded-md cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-[13px] text-stone-500 font-normal leading-relaxed mb-5">
              Enter the code your teacher gave you to add their subject.
            </p>

            <form onSubmit={handleAddSubjectSubmit} className="space-y-6">
              <input
                type="text"
                placeholder="e.g. COURSE101"
                value={subjectCode}
                onChange={(e) => setSubjectCode(e.target.value)}
                required
                className="w-full bg-stone-100/90 border border-stone-200/80 rounded-[14px] px-4 py-3.5 text-sm placeholder:text-stone-400 text-stone-900 outline-none focus:border-stone-400 transition-all font-medium"
              />

              <div className="flex justify-end gap-2.5 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsAddSubjectModalOpen(false);
                    setSubjectCode("");
                  }}
                  className="px-5 py-2 border border-stone-950 text-stone-950 font-bold text-[13px] rounded-full hover:bg-stone-50 transition-all active:scale-[0.97] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#f89b78] hover:bg-[#e65100] text-white font-bold text-[13px] rounded-full shadow-sm transition-all active:scale-[0.97] cursor-pointer"
                >
                  Add subject
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
