"use client";

import React from "react";
import Link from "next/link";
import TeacherSidebar from "@/components/teachersidebar";
import {
  CalendarDays,
  Users,
  FileText,
  Settings,
  LogOut,
  Search,
  Plus,
  ChevronDown,
  Trash2,
  X,
} from "lucide-react";

import {
  createSubject,
  createSession,
  deleteSession,
  getStoredTeacherSubjectId,
  getTeacherDashboardViewModel,
  persistTeacherSubjectId,
  startSession,
  TEACHER_SUBJECT_CHANGE_EVENT,
  type TeacherDashboardViewModel,
} from "@/lib/api";

type TeacherSubject = {
  id: string;
  code: string;
  name: string;
  displayShort: string;
  subtitle?: string;
  weeks: string;
  stats?: {
    avgReadiness?: string;
    semesterProgress?: string;
    progressCriteria?: string;
    sessionsRun?: number;
    studentsCaughtUp?: string;
  };
};

type TeacherSession = {
  id: number | string;
  week: string;
  title: string;
  status: "Completed" | "Active" | "Upcoming";
  segments: string[];
  avgReadiness: string;
  isLive?: boolean;
  date?: string;
  startTime?: string;
  endTime?: string;
};

function getLocalDateInputValue(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getLocalTimeInputValue(date = new Date()) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function addMinutesToTime(time: string, minutesToAdd: number) {
  const [hours, minutes] = time.split(":").map(Number);
  const date = new Date();
  date.setHours(hours || 0, minutes || 0, 0, 0);
  date.setMinutes(date.getMinutes() + minutesToAdd);
  return getLocalTimeInputValue(date);
}

function getDurationMinutes(startTime: string, endTime: string) {
  const [startHours, startMinutes] = startTime.split(":").map(Number);
  const [endHours, endMinutes] = endTime.split(":").map(Number);
  const startTotal = (startHours || 0) * 60 + (startMinutes || 0);
  let endTotal = (endHours || 0) * 60 + (endMinutes || 0);

  if (endTotal <= startTotal) {
    endTotal += 24 * 60;
  }

  return endTotal - startTotal;
}

export default function Page() {
  const [viewModel, setViewModel] = React.useState<TeacherDashboardViewModel>({
    subjects: [],
    sessionsBySubject: {},
  });
  const [isLoading, setIsLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState("");
  const [sessionsBySubject, setSessionsBySubject] = React.useState<
    Record<string, TeacherSession[]>
  >({});
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);
  const [selectedSubject, setSelectedSubject] = React.useState<TeacherSubject>(
    {
      id: "",
      code: "",
      name: "",
      displayShort: "",
      subtitle: "",
      weeks: "",
      stats: {
        avgReadiness: "N/A",
        semesterProgress: "0%",
        progressCriteria: "",
        sessionsRun: 0,
        studentsCaughtUp: "0/0",
      },
    }
  );
  const [searchQuery, setSearchQuery] = React.useState("");

  React.useEffect(() => {
    let ignore = false;

    getTeacherDashboardViewModel()
      .then((nextViewModel) => {
        if (ignore) return;
        setViewModel(nextViewModel);
        setSessionsBySubject(nextViewModel.sessionsBySubject);
        const storedSubjectId = getStoredTeacherSubjectId();
        setSelectedSubject(
          nextViewModel.subjects.find((subject) => subject.id === storedSubjectId) ??
          nextViewModel.subjects[0] ?? {
            id: "",
            code: "",
            name: "",
            displayShort: "",
            subtitle: "",
            weeks: "",
            stats: {
              avgReadiness: "N/A",
              semesterProgress: "0%",
              progressCriteria: "",
              sessionsRun: 0,
              studentsCaughtUp: "0/0",
            },
          },
        );
      })
      .catch((error) => {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load dashboard.",
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

  React.useEffect(() => {
    function handleSubjectChange(event: Event) {
      const subjectId = (event as CustomEvent<string>).detail;
      const subject = viewModel.subjects.find((item) => item.id === subjectId);
      if (subject) setSelectedSubject(subject);
    }

    window.addEventListener(TEACHER_SUBJECT_CHANGE_EVENT, handleSubjectChange);
    return () => {
      window.removeEventListener(
        TEACHER_SUBJECT_CHANGE_EVENT,
        handleSubjectChange,
      );
    };
  }, [viewModel.subjects]);

  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [sessionTitle, setSessionTitle] = React.useState("");
  const [sessionDate, setSessionDate] = React.useState(getLocalDateInputValue);
  const [sessionTime, setSessionTime] = React.useState("09:00");
  const [sessionEndTime, setSessionEndTime] = React.useState("12:00");
  const [isCreatingSession, setIsCreatingSession] = React.useState(false);

  const [isSubjectModalOpen, setIsSubjectModalOpen] = React.useState(false);
  const [subjectName, setSubjectName] = React.useState("");
  const [subjectCode, setSubjectCode] = React.useState("");

  React.useEffect(() => {
    document.documentElement.style.scrollbarGutter = "stable";
    return () => {
      document.documentElement.style.scrollbarGutter = "";
    };
  }, []);

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    const subjectCode = selectedSubject?.code;
    if (!subjectCode || isCreatingSession) return;

    const sessionDateTime = new Date(`${sessionDate}T${sessionTime}`);
    if (Number.isNaN(sessionDateTime.getTime())) {
      alert("Please choose a valid date and time.");
      return;
    }
    const durationMinutes = getDurationMinutes(sessionTime, sessionEndTime);
    if (durationMinutes < 5 || durationMinutes > 720) {
      alert("Please choose a class duration between 5 minutes and 12 hours.");
      return;
    }

    const week = `Week ${(sessionsBySubject[subjectCode]?.length ?? 0) + 1}`;

    setIsCreatingSession(true);
    try {
      const createdSession = await createSession({
        title: sessionTitle.trim(),
        week,
        date: sessionDateTime.toISOString(),
        durationMinutes,
        subjectId: selectedSubject.id,
      });

      const nextSession: TeacherSession = {
        id: createdSession.id,
        week: createdSession.week,
        title: createdSession.title,
        status: "Upcoming",
        segments: [
          "bg-stone-200",
          "bg-stone-200",
          "bg-stone-200",
          "bg-stone-200",
        ],
        avgReadiness: "0%",
        date: createdSession.date,
        startTime: sessionTime,
        endTime: sessionEndTime,
      };

      setSessionsBySubject((current) => ({
        ...current,
        [subjectCode]: [...(current[subjectCode] ?? []), nextSession],
      }));
      setIsModalOpen(false);
      setSessionTitle("");
      setSessionDate(getLocalDateInputValue());
      setSessionTime("09:00");
      setSessionEndTime("12:00");
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to create session.");
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const subject = await createSubject("teacher", {
        code: subjectCode,
        name: subjectName,
      });
      setViewModel((current) => ({
        subjects: [subject, ...current.subjects],
        sessionsBySubject: {
          ...current.sessionsBySubject,
          [subject.code]: [],
        },
      }));
      setSessionsBySubject((current) => ({
        ...current,
        [subject.code]: [],
      }));
      setSelectedSubject(subject);
      persistTeacherSubjectId(subject.id);
      setIsSubjectModalOpen(false);
      setSubjectName("");
      setSubjectCode("");
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to create subject.");
    }
  };

  const handleStartSession = async (sessionId: string) => {
    try {
      await startSession(sessionId);
      const subjectCode = selectedSubject.code;
      setSessionsBySubject((current) => ({
        ...current,
        [subjectCode]: (current[subjectCode] ?? []).map((session) =>
          session.id === sessionId
            ? { ...session, status: "Active", isLive: true }
            : session,
        ),
      }));
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to start session.");
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      const subjectCode = selectedSubject.code;
      setSessionsBySubject((current) => ({
        ...current,
        [subjectCode]: (current[subjectCode] ?? []).filter(
          (session) => session.id !== sessionId,
        ),
      }));
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to delete session.");
    }
  };

  const currentSessions: TeacherSession[] =
    selectedSubject?.code && sessionsBySubject[selectedSubject.code]
      ? sessionsBySubject[selectedSubject.code]
      : [];
  const filteredSessions = (currentSessions || []).filter((session: any) => {
    const query = searchQuery.toLowerCase().trim();
    return (
      session.title?.toLowerCase().includes(query) ||
      session.week?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <TeacherSidebar />

      {/* RIGHT MAIN CONTENT */}
      <main
        suppressHydrationWarning
        className="flex-1 pl-64 px-8 pt-14 pb-8 relative overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          {isLoading && (
            <div className="rounded-2xl border border-stone-200/70 bg-white/90 p-6 text-sm font-semibold text-stone-500 shadow-sm">
              Loading teacher dashboard...
            </div>
          )}

          {!isLoading && loadError && (
            <div className="rounded-2xl border border-red-100 bg-white/90 p-6 text-sm font-semibold text-red-500 shadow-sm">
              {loadError}
            </div>
          )}

          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div className="max-w-2xl">
              <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
                {selectedSubject?.code} - {selectedSubject?.name}
              </h2>
              <p className="text-sm text-stone-500 mt-1.5 leading-relaxed">
                {selectedSubject?.subtitle}
              </p>
            </div>

            <div suppressHydrationWarning className="flex items-center gap-3">
              <button
                onClick={() => setIsSubjectModalOpen(true)}
                className="flex items-center gap-1.5 px-4 h-9 bg-white border border-stone-200 text-stone-700 hover:text-[#d84315] text-xs font-bold rounded-full shadow-sm transition-all active:scale-[0.98] cursor-pointer"
              >
                <Plus size={14} />
                New course
              </button>

              <div className="relative w-64">
                <Search
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
                />
                <input
                  type="text"
                  placeholder="Search sessions"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 h-9 bg-white border border-stone-200/80 rounded-full text-xs placeholder:text-stone-300 outline-none focus:border-orange-500/50"
                />
              </div>

              <button
                onClick={() => setIsModalOpen(true)}
                disabled={!selectedSubject.id}
                className="flex items-center gap-1.5 px-4 h-9 bg-[#e65100] hover:bg-[#d84315] text-white text-xs font-bold rounded-full shadow-sm transition-all active:scale-[0.98] cursor-pointer"
              >
                <Plus size={14} />
                New session
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                label: "Avg readiness",
                value: selectedSubject?.stats?.avgReadiness ?? "N/A",
                subtext: "across active sessions",
              },
              {
                label: "Semester progress",
                value: selectedSubject?.stats?.semesterProgress ?? "0%",
                subtext: selectedSubject?.stats?.progressCriteria ?? "",
              },
              {
                label: "Sessions run",
                value: selectedSubject?.stats?.sessionsRun ?? 0,
                subtext: "this semester",
              },
              {
                label: "Students caught up",
                value: selectedSubject?.stats?.studentsCaughtUp ?? "0/0",
                subtext: "latest week",
              },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-2xl border border-stone-200/70 bg-white/90 p-4 shadow-sm text-left backdrop-blur-sm"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-400">
                  {item.label}
                </p>
                <p className="text-xl font-bold text-stone-900 mt-2">
                  {item.value}
                </p>
                <p className="text-[10px] text-stone-400 mt-1">
                  {item.subtext}
                </p>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              <h3 className="text-sm font-bold text-stone-800">
                Sessions ({selectedSubject?.weeks})
              </h3>
              <p className="text-xs text-stone-400 mt-1">
                Track weekly progress and keep each session easy to review.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 min-h-[480px] items-start content-start pb-12">
            {filteredSessions.length > 0 ? (
              filteredSessions.map((session: TeacherSession) => {
                const isUpcoming = session.status === "Upcoming";
                const CardWrapper = isUpcoming ? "div" : Link;

                const wrapperProps = isUpcoming
                  ? {
                      className:
                        "bg-white/95 border border-stone-200/70 rounded-2xl p-4 flex flex-col h-full shadow-sm transition-all text-left hover:shadow-md",
                    }
                  : {
                      href: `/teacher/session/${session.id}`,
                      className:
                        "bg-white/95 border border-stone-200/70 rounded-2xl p-4 flex flex-col h-full shadow-sm hover:shadow-md transition-all text-left",
                    };

                return (
                  <CardWrapper key={session.id} {...(wrapperProps as any)}>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider">
                          {session.week}
                        </span>

                        <div className="flex items-center gap-1.5">
                          {session.status === "Completed" && (
                            <span className="px-2.5 py-0.5 bg-[#e6f4ea] text-[#137333] rounded-full text-[10px] font-bold border border-[#ceead6] shadow-sm">
                              Completed
                            </span>
                          )}
                          {session.status === "Active" && (
                            <span className="px-2.5 py-0.5 bg-[#fff3ed] text-[#d84315] rounded-full text-[10px] font-bold border border-orange-100 shadow-sm">
                              Active
                            </span>
                          )}
                          {session.status === "Upcoming" && (
                            <>
                              <span className="px-2.5 py-0.5 bg-white text-stone-500 border border-stone-200 rounded-full text-[10px] font-semibold shadow-sm">
                                Upcoming
                              </span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteSession(String(session.id));
                                }}
                                className="w-7 h-7 flex items-center justify-center bg-white text-stone-500 border border-stone-200 rounded-xl hover:text-rose-600 hover:border-rose-200 transition-colors shadow-sm cursor-pointer active:scale-[0.95]"
                                title="Delete session"
                              >
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      <h4 className="text-base font-bold text-stone-900 leading-snug mb-3">
                        {session.title}
                      </h4>

                      {session.startTime && session.endTime && (
                        <div className="mb-3 rounded-xl bg-stone-50 px-3 py-2 text-[11px] font-semibold text-stone-500">
                          Class time: {session.startTime} - {session.endTime}
                          <span className="block text-stone-400">
                            Attendance slots are spread across this time.
                          </span>
                        </div>
                      )}

                      <div className="grid grid-cols-4 gap-1 mb-2">
                        {(() => {
                          const readinessValue = Number(
                            session.avgReadiness?.replace("%", "") ?? "0",
                          );
                          const fillCount =
                            session.status === "Completed"
                              ? 4
                              : session.status === "Active"
                                ? Math.min(
                                    4,
                                    Math.max(
                                      0,
                                      Math.round(readinessValue / 25),
                                    ),
                                  )
                                : 0;

                          return [0, 1, 2, 3].map((index) => {
                            let segBg = "bg-stone-200";

                            if (session.status === "Completed") {
                              segBg = "bg-emerald-400";
                            } else if (
                              session.status === "Active" &&
                              index < fillCount
                            ) {
                              segBg = "bg-orange-400";
                            }

                            return (
                              <div
                                key={index}
                                className={`h-1.5 rounded-full ${segBg}`}
                              />
                            );
                          });
                        })()}
                      </div>

                      <div className="flex justify-between items-center text-[11px] text-stone-400 font-medium mb-2">
                        <span>Avg readiness</span>
                        <span
                          className={`font-semibold ${session.status !== "Upcoming" ? "text-stone-700" : ""}`}
                        >
                          {session.avgReadiness}
                        </span>
                      </div>
                    </div>

                    {(session.status === "Upcoming" || session.isLive) && (
                      <div className="pt-2.5 mt-2 border-t border-stone-100 flex flex-col justify-center">
                        {session.status === "Upcoming" && (
                          <button
                            type="button"
                            onClick={() => {
                              handleStartSession(String(session.id));
                            }}
                            className="w-full py-2 bg-[#fff8f5] border border-orange-200/80 text-[13px] text-[#d84315] font-bold rounded-full flex items-center justify-center gap-1 hover:bg-[#fff3ed] hover:border-orange-300 transition-all active:scale-[0.99] cursor-pointer shadow-sm"
                          >
                            {"Start this session ->"}
                          </button>
                        )}

                        {session.isLive && (
                          <div className="text-[11px] text-rose-500 font-bold flex items-center gap-1.5 py-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                            <span className="hover:underline cursor-pointer">
                              Live now - view questions
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </CardWrapper>
                );
              })
            ) : (
              <div className="col-span-full py-32 text-center select-none">
                <p className="text-xs font-bold text-stone-500">
                  No sessions found
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* NEW SESSION MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-[1px] flex items-center justify-center z-50">
          <div className="bg-white w-[460px] rounded-[28px] p-7 shadow-2xl relative max-w-[90%] mx-auto text-left">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-stone-900 tracking-tight">
                New session
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-stone-400/90 mb-1.5">
                  Session title
                </label>
                <input
                  type="text"
                  placeholder="e.g. VPC networking"
                  value={sessionTitle}
                  onChange={(e) => setSessionTitle(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-stone-50 rounded-[14px] text-xs font-medium text-stone-900 placeholder:text-stone-400/80 outline-none border border-stone-300 focus:border-stone-400 transition-all"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-[11px] font-semibold text-stone-400/90 mb-1.5">
                    Date
                  </label>
                  <input
                    type="date"
                    value={sessionDate}
                    onChange={(e) => setSessionDate(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-stone-50 rounded-[14px] text-xs font-medium text-stone-700 outline-none border border-stone-300 focus:border-stone-400 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-stone-400/90 mb-1.5">
                    Start time
                  </label>
                  <input
                    type="time"
                    value={sessionTime}
                    onChange={(e) => {
                      setSessionTime(e.target.value);
                      setSessionEndTime(addMinutesToTime(e.target.value, 180));
                    }}
                    required
                    className="w-full px-4 py-3 bg-stone-50 rounded-[14px] text-xs font-medium text-stone-700 outline-none border border-stone-300 focus:border-stone-400 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-stone-400/90 mb-1.5">
                    End time
                  </label>
                  <input
                    type="time"
                    value={sessionEndTime}
                    onChange={(e) => setSessionEndTime(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-stone-50 rounded-[14px] text-xs font-medium text-stone-700 outline-none border border-stone-300 focus:border-stone-400 transition-all"
                  />
                </div>
              </div>
              <div className="rounded-2xl bg-orange-50 px-4 py-3 text-xs text-stone-600 ring-1 ring-orange-100">
                Attendance will open at different times for each student
                between {sessionTime} and {sessionEndTime}.
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-6 py-2 border border-stone-950 text-xs font-bold text-stone-950 rounded-full bg-white hover:bg-stone-50 transition-all active:scale-[0.97] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingSession}
                  className="px-6 py-2 bg-[#f5a982] hover:bg-[#e2936a] text-xs font-bold text-white rounded-full shadow-sm transition-all active:scale-[0.97] cursor-pointer"
                >
                  {isCreatingSession ? "Creating..." : "Create session"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD SUBJECT MODAL */}
      {isSubjectModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-[1px] flex items-center justify-center z-50">
          <div className="bg-white w-[460px] rounded-[28px] p-7 shadow-2xl relative max-w-[90%] mx-auto text-left">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold text-stone-950 tracking-tight">
                Add a subject
              </h3>
              <button
                onClick={() => setIsSubjectModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-[13px] text-stone-500 font-medium leading-relaxed mb-6">
              Create a new subject. You can add as many weekly sessions to it as
              you need.
            </p>

            <form onSubmit={handleCreateSubject} className="space-y-5">
              <div>
                <label className="block text-[13px] font-bold text-stone-600 mb-1.5">
                  Subject name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Database Systems"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-stone-50 rounded-[14px] text-xs font-medium text-stone-900 placeholder:text-stone-400/70 outline-none border border-stone-300 focus:border-stone-400 transition-all"
                />
              </div>

              <div>
                <label className="block text-[13px] font-bold text-stone-600 mb-1.5">
                  Subject code
                </label>
                <input
                  type="text"
                  placeholder="e.g. CS221"
                  value={subjectCode}
                  onChange={(e) => setSubjectCode(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-stone-50 rounded-[14px] text-xs font-medium text-stone-900 placeholder:text-stone-400/70 outline-none border border-stone-300 focus:border-stone-400 transition-all"
                />
              </div>

              <div className="flex justify-center sm:justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsSubjectModalOpen(false)}
                  className="px-7 py-2.5 border border-stone-950 text-[13px] font-bold text-stone-950 rounded-full bg-white hover:bg-stone-50 transition-all active:scale-[0.97] cursor-pointer"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="px-7 py-2.5 bg-[#f5a982] hover:bg-[#e2936a] text-[13px] font-bold text-white rounded-full transition-all active:scale-[0.97] cursor-pointer"
                >
                  Create subject
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
