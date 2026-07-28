"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  TrendingUp,
  FileText,
  LogOut,
  ChevronDown,
  Plus,
  X,
  CheckCircle2,
  AlertTriangle,
  MessageSquare,
  BookOpen,
} from "lucide-react";

import {
  getStudentDashboardViewModel,
  getStudentProgressViewModel,
  type AppSubject,
  type StudentDashboardViewModel,
  type StudentProgressViewModel,
} from "@/lib/api";

const emptySubject: AppSubject = {
  id: "",
  code: "",
  name: "",
  displayShort: "",
  weeks: "",
};

export default function MyProgressPage() {
  const [dashboardViewModel, setDashboardViewModel] =
    useState<StudentDashboardViewModel>({
      subjects: [],
      sessionsBySubject: {},
      attendance: {
        presentCount: 0,
        totalActiveSessions: 0,
      },
    });
  const [progressViewModel, setProgressViewModel] =
    useState<StudentProgressViewModel>({
      subjectCode: "",
      stats: [],
      progress: [],
      sessionInsights: [],
    });
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<AppSubject>(emptySubject);
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [subjectCode, setSubjectCode] = useState("");

  const loadProgressForSubject = async (subject: AppSubject) => {
    setSelectedSubject(subject);
    setIsDropdownOpen(false);
    setLoadError("");
    setIsLoading(true);
    try {
      const progress = await getStudentProgressViewModel(subject.code);
      setProgressViewModel(progress);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Failed to load progress.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;

    async function load() {
      try {
        const dashboard = await getStudentDashboardViewModel();
        const firstSubject = dashboard.subjects[0] ?? emptySubject;
        const progress = await getStudentProgressViewModel(firstSubject.code);
        if (ignore) return;
        setDashboardViewModel(dashboard);
        setSelectedSubject(firstSubject);
        setProgressViewModel(progress);
      } catch (error) {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load progress.",
          );
        }
      } finally {
        if (!ignore) setIsLoading(false);
      }
    }

    load();
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

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      {/* ================= 1. LEFT SIDEBAR ================= */}
      <aside className="w-64 bg-white border-r border-stone-200/60 flex flex-col justify-between fixed h-full z-20">
        <div>
          {/* Logo & Header */}
          <div className="p-5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#e65100]" />
            <h1 className="text-md font-bold tracking-tight text-stone-950">
              Learning Companion
            </h1>
          </div>

          <div className="px-3 mb-6 relative">
            <div
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center justify-between p-2.5 bg-white border border-stone-200/80 rounded-xl cursor-pointer hover:bg-stone-50 transition-colors select-none"
            >
              <div className="text-left min-w-0 flex-1">
                <p className="text-[13px] font-bold text-stone-900 truncate pr-1">
                  {selectedSubject.displayShort}
                </p>
                <p className="text-[10px] text-stone-400 font-medium">
                  {dashboardViewModel.subjects.length} subjects
                </p>
              </div>
              <ChevronDown
                size={16}
                className={`text-stone-400 transition-transform duration-200 flex-shrink-0 ${isDropdownOpen ? "rotate-180" : ""}`}
              />
            </div>

            {/* Dropdown Menu Popup */}
            {isDropdownOpen && (
              <div className="absolute left-3 right-3 top-full mt-1.5 bg-white border border-stone-200 shadow-xl rounded-xl z-30 overflow-hidden divide-y divide-stone-100">
                <div>
                  {dashboardViewModel.subjects.map((subject) => {
                    const isSelected = subject.id === selectedSubject.id;
                    return (
                      <div
                        key={subject.id}
                        onClick={() => void loadProgressForSubject(subject)}
                        className={`p-3 text-left cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-[#fff3ed] text-[#d84315]"
                            : "bg-white text-stone-900 hover:bg-stone-50"
                        }`}
                      >
                        <p className="text-xs font-bold truncate">
                          {subject.displayShort}
                        </p>
                        <p
                          className={`text-[10px] font-medium mt-0.5 ${
                            isSelected ? "text-[#d84315]/70" : "text-stone-400"
                          }`}
                        >
                          {subject.weeks}
                        </p>
                      </div>
                    );
                  })}
                </div>

                <div
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setIsAddSubjectModalOpen(true);
                  }}
                  className="p-3 text-left cursor-pointer hover:bg-stone-50 transition-colors flex items-center gap-2 text-[#d84315] font-bold text-xs"
                >
                  <Plus size={14} />
                  <span>Add subject</span>
                </div>
              </div>
            )}
          </div>

          {/* Nav Links */}
          <nav className="px-3 space-y-5">
            {/* Student Section */}
            <div>
              <p className="px-2 text-[10px] font-bold text-stone-400 uppercase tracking-wider mb-1.5">
                Student
              </p>
              <div className="space-y-0.5">
                <Link
                  href="/student/dashboard"
                  className="flex items-center gap-2.5 px-3 py-2 text-[14px] font-medium text-stone-600 hover:bg-stone-50 hover:text-stone-900 rounded-lg transition-colors"
                >
                  <Layers size={15} className="text-stone-400" />
                  Sessions
                </Link>
                <Link
                  href="/student/material"
                  className="flex items-center gap-2.5 px-3 py-2 text-[14px] font-medium text-stone-600 hover:bg-stone-50 hover:text-stone-900 rounded-lg transition-colors"
                >
                  <FileText size={15} className="text-stone-400" />
                  Materials
                </Link>
                <Link
                  href="/student/progress"
                  className="flex items-center gap-2.5 px-3 py-2 text-[14px] font-bold text-[#d84315] bg-[#fff3ed] rounded-lg"
                >
                  <TrendingUp size={15} />
                  My progress
                </Link>
              </div>
            </div>
          </nav>
        </div>

        {/* Profile Bottom */}
        <div className="p-4 border-t border-stone-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-[11px] font-bold text-orange-700">
              ST
            </div>
            <div className="text-left">
              <p className="text-xs font-bold text-stone-900 leading-tight">
                Student
              </p>
              <p className="text-[10px] text-stone-400 font-medium leading-none">
                Student
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-stone-400 hover:text-stone-900 hover:bg-stone-50 rounded-md transition-colors"
            title="Log out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* ================= 2. MAIN CONTENT ================= */}
      <main
        suppressHydrationWarning
        className="flex-1 pl-64 p-8 pt-14 pb-8 relative overflow-hidden text-left"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
                My progress
              </h2>
              <p className="text-xs text-stone-400 mt-1">
                An overview of your readiness across this subject.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {progressViewModel.stats.map((stat, idx) => (
              <div
                key={idx}
                className="bg-white border border-stone-200/70 rounded-2xl p-5 shadow-sm text-left"
              >
                <p className="text-[11px] font-semibold text-stone-400 mb-1">
                  {stat.label}
                </p>
                <p className="text-2xl font-bold text-stone-900 tracking-tight mb-1">
                  {stat.value}
                </p>
                <p className="text-[10px] font-medium text-stone-400">
                  {stat.subtext}
                </p>
              </div>
            ))}
          </div>

          {loadError && (
            <div className="bg-white border border-red-100 rounded-2xl p-4 text-sm font-medium text-red-600 shadow-sm">
              {loadError}
            </div>
          )}

          {isLoading && (
            <div className="bg-white border border-stone-200/70 rounded-2xl p-5 text-sm font-semibold text-stone-500 shadow-sm">
              Loading your learning profile...
            </div>
          )}

          <div className="space-y-4">
            <h2 className="text-xs font-bold text-stone-400 uppercase tracking-wider">
              Readiness by session
            </h2>

            <div className="bg-white border border-stone-200/70 rounded-2xl p-6 shadow-sm divide-y divide-stone-100">
              {progressViewModel.progress.map((item) => (
                <div
                  key={item.id}
                  className="py-4 first:pt-0 last:pb-0 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-stone-800">
                      {item.weekTitle}
                    </span>
                    <span className="text-xs font-semibold text-stone-400">
                      {item.percentage > 0 ? `${item.percentage}%` : "-"}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1">
                    <div className="flex-1 h-2 bg-stone-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} transition-all duration-500`}
                        style={{ width: `${item.percentage}%` }}
                      />
                    </div>
                  </div>

                  <div className="text-[11px] font-medium text-stone-400 pt-0.5">
                    {item.status}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <h2 className="text-xs font-bold text-stone-400 uppercase tracking-wider">
                Strengths and focus areas
              </h2>
              <p className="text-xs text-stone-500 mt-1">
                Built from your quiz results and the questions you asked in each session.
              </p>
            </div>

            {progressViewModel.sessionInsights.length === 0 && !isLoading ? (
              <div className="bg-white border border-stone-200/70 rounded-2xl p-6 text-sm font-medium text-stone-500 shadow-sm">
                No quiz or chat activity has been recorded yet.
              </div>
            ) : (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {progressViewModel.sessionInsights.map((insight) => (
                  <section
                    key={insight.id}
                    className="bg-white border border-stone-200/70 rounded-2xl p-5 shadow-sm"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wider text-stone-400">
                          {insight.status}
                        </p>
                        <h3 className="mt-1 text-lg font-bold text-stone-950">
                          {insight.weekTitle}
                        </h3>
                        <p className="mt-1 text-xs font-medium text-stone-500">
                          Latest quiz: {insight.latestQuizResult}
                        </p>
                      </div>
                      <div className="rounded-2xl bg-[#fff3ed] px-4 py-3 text-right">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-[#d84315]">
                          Readiness
                        </p>
                        <p className="text-2xl font-bold text-stone-950">
                          {insight.readiness}%
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 grid grid-cols-2 gap-3">
                      <div className="rounded-xl bg-stone-50 px-3 py-2">
                        <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-stone-400">
                          <BookOpen size={13} />
                          Quiz
                        </div>
                        <p className="mt-1 text-sm font-bold text-stone-900">
                          {insight.quizAttempts} attempts
                        </p>
                      </div>
                      <div className="rounded-xl bg-stone-50 px-3 py-2">
                        <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-stone-400">
                          <MessageSquare size={13} />
                          Chat
                        </div>
                        <p className="mt-1 text-sm font-bold text-stone-900">
                          {insight.chatQuestions} questions
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 lg:grid-cols-2">
                      <div>
                        <div className="mb-2 flex items-center gap-2 text-xs font-bold text-emerald-700">
                          <CheckCircle2 size={15} />
                          Strengths
                        </div>
                        {insight.strengths.length ? (
                          <div className="space-y-2">
                            {insight.strengths.map((item) => (
                              <p
                                key={item}
                                className="rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-900"
                              >
                                {item}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs font-medium text-stone-400">
                            Complete a quiz to reveal strengths.
                          </p>
                        )}
                      </div>

                      <div>
                        <div className="mb-2 flex items-center gap-2 text-xs font-bold text-orange-700">
                          <AlertTriangle size={15} />
                          Needs work
                        </div>
                        {insight.weaknesses.length ? (
                          <div className="space-y-2">
                            {insight.weaknesses.map((item) => (
                              <p
                                key={item}
                                className="rounded-xl border border-orange-100 bg-orange-50 px-3 py-2 text-xs font-medium text-orange-950"
                              >
                                {item}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs font-medium text-stone-400">
                            No clear weakness detected yet.
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="mt-5 border-t border-stone-100 pt-4">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-stone-400">
                        Suggested focus
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {(insight.suggestedFocus.length ? insight.suggestedFocus : ["Ask more questions or submit a quiz for better guidance"]).map((item) => (
                          <span
                            key={item}
                            className="rounded-full border border-stone-200 bg-white px-3 py-1 text-xs font-semibold text-stone-600"
                          >
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>

                    {insight.references.length > 0 && (
                      <div className="mt-4">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-stone-400">
                          Material references
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {insight.references.map((reference) => (
                            <span
                              key={`${reference.materialId}-${reference.fileName}-${reference.pageNumber}`}
                              className="rounded-full bg-[#fff7ed] px-3 py-1 text-[11px] font-semibold text-stone-600"
                            >
                              {reference.fileName}
                              {reference.pageNumber ? ` p.${reference.pageNumber}` : ""}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-5 flex flex-wrap gap-2">
                      <Link
                        href={`/student/session/${insight.id}`}
                        className="rounded-full bg-[#e65100] px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-[#d84315]"
                      >
                        Open session
                      </Link>
                      <Link
                        href={`/student/session/${insight.id}/quiz`}
                        className="rounded-full border border-stone-900 px-4 py-2 text-xs font-bold text-stone-900 hover:bg-stone-50"
                      >
                        Review quiz
                      </Link>
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ================= 3. ADD A SUBJECT MODAL POPUP ================= */}
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
