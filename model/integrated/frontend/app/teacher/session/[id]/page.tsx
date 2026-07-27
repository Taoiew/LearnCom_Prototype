"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Camera,
  CalendarPlus,
  ChevronLeft,
  ClipboardCheck,
  Image as ImageIcon,
  Layers,
  MessageSquareText,
  Users,
} from "lucide-react";
import TeacherSidebar from "@/components/teachersidebar";
import {
  analyzeNextClassPreview,
  createNextClassPreview,
  createRevisionNote,
  getTeacherDashboardViewModel,
  getTeacherSessionSummary,
  publishNextClassPreview,
  publishRevisionNote,
  type NextClassPreview,
  type TeacherAnswerReference,
  type TeacherSession,
  type TeacherSessionSummary,
} from "@/lib/api";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatClassTime(session: TeacherSessionSummary["session"]) {
  const start = new Date(session.date);
  const end = new Date(start.getTime() + session.durationMinutes * 60 * 1000);
  return `${formatDateTime(start.toISOString())} - ${end.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function formatMaterialRef(ref: {
  materialId: string;
  fileName: string;
  pageNumber: number | null;
}) {
  const page = ref.pageNumber ? `, page ${ref.pageNumber}` : "";
  return `${ref.fileName} (${ref.materialId}${page})`;
}

function formatAnswerReference(ref: TeacherAnswerReference) {
  if (ref.sourceType === "EXTERNAL_AI") {
    return ref.sourceName ?? ref.provider ?? "External AI";
  }

  const materialLabel = ref.materialFileName ?? ref.materialId ?? ref.sourceName ?? "Material";
  return `${materialLabel}${ref.pageNumber ? `, page ${ref.pageNumber}` : ""}`;
}

function formatReadiness(value: string) {
  if (value === "READY") return "Ready";
  if (value === "PARTIAL") return "Partial";
  return "Needs review";
}

export default function TeacherSessionPage() {
  const params = useParams();
  const sessionId = String(params?.id ?? "");
  const [summary, setSummary] = useState<TeacherSessionSummary | null>(null);
  const [loadError, setLoadError] = useState("");
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [teacherSessions, setTeacherSessions] = useState<TeacherSession[]>([]);
  const [nextSessionId, setNextSessionId] = useState("");
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewContent, setPreviewContent] = useState("");
  const [previewActionError, setPreviewActionError] = useState("");
  const [isPreviewSaving, setIsPreviewSaving] = useState(false);
  const [revisionTopic, setRevisionTopic] = useState("");
  const [revisionText, setRevisionText] = useState("");

  useEffect(() => {
    let ignore = false;

    getTeacherSessionSummary(sessionId)
      .then((nextSummary) => {
        if (!ignore) {
          setSummary(nextSummary);
          setLoadError("");
        }
      })
      .catch((error) => {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load session summary.",
          );
        }
      });

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  useEffect(() => {
    let ignore = false;

    getTeacherDashboardViewModel()
      .then((viewModel) => {
        if (ignore) return;
        setTeacherSessions(Object.values(viewModel.sessionsBySubject).flat());
      })
      .catch(() => {
        if (!ignore) setTeacherSessions([]);
      });

    return () => {
      ignore = true;
    };
  }, []);

  const refreshSummary = async () => {
    const nextSummary = await getTeacherSessionSummary(sessionId);
    setSummary(nextSummary);
  };

  const handleCreatePreview = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!nextSessionId || !previewTitle.trim()) {
      setPreviewActionError("Choose the next session and add a preview title.");
      return;
    }

    setIsPreviewSaving(true);
    setPreviewActionError("");
    try {
      await createNextClassPreview({
        currentSessionId: sessionId,
        nextSessionId,
        title: previewTitle,
        previewContent,
      });
      await refreshSummary();
      setIsPreviewModalOpen(false);
      setNextSessionId("");
      setPreviewTitle("");
      setPreviewContent("");
    } catch (error) {
      setPreviewActionError(
        error instanceof Error ? error.message : "Could not create preview.",
      );
    } finally {
      setIsPreviewSaving(false);
    }
  };

  const handlePublishPreview = async (previewId: string) => {
    try {
      await publishNextClassPreview(previewId);
      await refreshSummary();
    } catch (error) {
      setPreviewActionError(
        error instanceof Error ? error.message : "Could not publish preview.",
      );
    }
  };

  const handleAnalyzePreview = async (previewId: string) => {
    try {
      await analyzeNextClassPreview(previewId);
      await refreshSummary();
    } catch (error) {
      setPreviewActionError(
        error instanceof Error ? error.message : "Could not analyze preview.",
      );
    }
  };

  const handleCreateRevision = async (preview: NextClassPreview) => {
    if (!preview.summary?.id || !revisionTopic.trim() || !revisionText.trim()) {
      setPreviewActionError("Add a topic and revision note first.");
      return;
    }

    try {
      const note = await createRevisionNote({
        summaryId: preview.summary.id,
        topic: revisionTopic,
        explanation: revisionText,
        priority: "medium",
      });
      await publishRevisionNote(note.id);
      setRevisionTopic("");
      setRevisionText("");
      await refreshSummary();
    } catch (error) {
      setPreviewActionError(
        error instanceof Error ? error.message : "Could not save revision note.",
      );
    }
  };

  const stats = summary
    ? [
        {
          label: "Students attended",
          value: summary.stats.studentsAttended,
          subtext: `${summary.stats.attendancePhotos} photo files`,
          icon: Users,
        },
        {
          label: "Questions asked",
          value: summary.stats.questionsAsked,
          subtext: "student chat messages",
          icon: MessageSquareText,
        },
        {
          label: "Top topic",
          value: summary.stats.topTopic,
          subtext: "from question text",
          icon: MessageSquareText,
        },
        {
          label: "Chat images",
          value: summary.stats.chatImagesSent,
          subtext: "files sent in chat",
          icon: ImageIcon,
        },
      ]
    : [];
  const quizOverview = summary?.quizOverview ?? {
    totalAttempts: 0,
    submittedAttempts: 0,
    averageScore: 0,
    studentsSubmitted: 0,
    studentsPassed: 0,
    phases: [
      {
        phase: "BEFORE" as const,
        attempts: 0,
        submittedAttempts: 0,
        studentsSubmitted: 0,
        averageScore: 0,
        readyCount: 0,
        partialCount: 0,
        notReadyCount: 0,
      },
      {
        phase: "AFTER" as const,
        attempts: 0,
        submittedAttempts: 0,
        studentsSubmitted: 0,
        averageScore: 0,
        readyCount: 0,
        partialCount: 0,
        notReadyCount: 0,
      },
    ],
    criteriaBreakdown: [],
    recentAttempts: [],
  };
  const nextClassReadiness = summary?.nextClassReadiness ?? [];

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <TeacherSidebar />
      <main
        className="flex-1 pl-64 px-8 pt-12 pb-10 relative overflow-y-auto"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          <Link
            href="/teacher/dashboard"
            className="inline-flex items-center gap-1 text-xs font-semibold text-stone-500 hover:text-stone-800 transition-colors"
          >
            <ChevronLeft size={16} /> Sessions
          </Link>

          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold text-stone-400">
              {summary?.session.subject.name ?? "Session summary"}
            </p>
            <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
              {summary?.session.title ?? "Loading session"}
            </h2>
            <p className="text-xs text-stone-500">
              {loadError ||
                (summary
                  ? `${summary.session.status} / ${summary.session.phase} / ${formatClassTime(summary.session)}`
                  : "Loading real chat and attendance data...")}
            </p>
          </div>

          {summary ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.label}
                      className="rounded-2xl border border-stone-200/70 bg-white/90 p-4 shadow-sm"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-400">
                          {item.label}
                        </p>
                        <Icon size={16} className="text-[#e65100]" />
                      </div>
                      <p className="mt-2 text-xl font-bold text-stone-900 truncate">
                        {item.value}
                      </p>
                      <p className="mt-1 text-[10px] text-stone-400">
                        {item.subtext}
                      </p>
                    </div>
                  );
                })}
              </div>

              <section className="rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Quiz overview
                    </h3>
                    <p className="text-xs text-stone-500">
                      Pre-class readiness and post-class mastery results for this session.
                    </p>
                  </div>
                  <ClipboardCheck size={18} className="text-[#e65100]" />
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-4">
                  <div className="rounded-xl border border-stone-100 bg-stone-50/70 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                      Avg score
                    </p>
                    <p className="mt-2 text-2xl font-bold text-stone-900">
                      {quizOverview.averageScore}%
                    </p>
                    <p className="mt-1 text-[11px] text-stone-500">
                      {quizOverview.submittedAttempts} submitted attempts
                    </p>
                  </div>
                  <div className="rounded-xl border border-stone-100 bg-stone-50/70 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                      Students submitted
                    </p>
                    <p className="mt-2 text-2xl font-bold text-stone-900">
                      {quizOverview.studentsSubmitted}
                    </p>
                    <p className="mt-1 text-[11px] text-stone-500">
                      across before and after quizzes
                    </p>
                  </div>
                  <div className="rounded-xl border border-stone-100 bg-stone-50/70 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                      Passed after class
                    </p>
                    <p className="mt-2 text-2xl font-bold text-stone-900">
                      {quizOverview.studentsPassed}
                    </p>
                    <p className="mt-1 text-[11px] text-stone-500">
                      latest post-quiz marked ready
                    </p>
                  </div>
                  <div className="rounded-xl border border-stone-100 bg-stone-50/70 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                      Total attempts
                    </p>
                    <p className="mt-2 text-2xl font-bold text-stone-900">
                      {quizOverview.totalAttempts}
                    </p>
                    <p className="mt-1 text-[11px] text-stone-500">
                      generated quizzes in this session
                    </p>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div className="space-y-3">
                    {quizOverview.phases.map((phase) => (
                      <div
                        key={phase.phase}
                        className="rounded-xl border border-stone-100 bg-white p-4"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#e65100]">
                              {phase.phase === "BEFORE" ? "Before class" : "After class"}
                            </p>
                            <p className="mt-1 text-sm font-bold text-stone-900">
                              {phase.submittedAttempts}/{phase.attempts} attempts submitted
                            </p>
                          </div>
                          <p className="text-xl font-bold text-stone-900">
                            {phase.averageScore}%
                          </p>
                        </div>
                        <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px] font-semibold">
                          <div className="rounded-lg bg-emerald-50 px-2 py-2 text-emerald-700">
                            {phase.readyCount} ready
                          </div>
                          <div className="rounded-lg bg-amber-50 px-2 py-2 text-amber-700">
                            {phase.partialCount} partial
                          </div>
                          <div className="rounded-lg bg-rose-50 px-2 py-2 text-rose-700">
                            {phase.notReadyCount} review
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="rounded-xl border border-stone-100 bg-white p-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                      Criteria needing attention
                    </p>
                    <div className="mt-3 max-h-[220px] space-y-2 overflow-y-auto pr-1">
                      {quizOverview.criteriaBreakdown.length > 0 ? (
                        quizOverview.criteriaBreakdown.map((criterion) => (
                          <div
                            key={criterion.criteriaId}
                            className="rounded-lg bg-stone-50 px-3 py-2"
                          >
                            <p className="line-clamp-1 text-xs font-bold text-stone-800">
                              {criterion.description}
                            </p>
                            <p className="mt-1 text-[11px] text-stone-500">
                              {criterion.notMetCount} not met, {criterion.partialCount} partial, {criterion.metCount} met
                            </p>
                          </div>
                        ))
                      ) : (
                        <p className="rounded-lg bg-stone-50 px-3 py-3 text-xs font-semibold text-stone-500">
                          No submitted quiz criteria yet.
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {quizOverview.recentAttempts.length > 0 && (
                  <div className="mt-4 overflow-hidden rounded-xl border border-stone-100">
                    <div className="max-h-[260px] overflow-auto">
                      <table className="w-full min-w-[680px] border-collapse bg-white text-left text-xs">
                        <thead className="bg-stone-50 text-[10px] uppercase tracking-[0.16em] text-stone-400">
                          <tr>
                            <th className="px-4 py-3 font-bold">Student</th>
                            <th className="px-4 py-3 font-bold">Quiz</th>
                            <th className="px-4 py-3 font-bold">Score</th>
                            <th className="px-4 py-3 font-bold">Result</th>
                            <th className="px-4 py-3 font-bold">Submitted</th>
                          </tr>
                        </thead>
                        <tbody>
                          {quizOverview.recentAttempts.map((attempt) => (
                            <tr key={attempt.quizId} className="border-t border-stone-100">
                              <td className="px-4 py-3 font-semibold text-stone-800">
                                {attempt.studentName}
                              </td>
                              <td className="px-4 py-3 text-stone-600">
                                {attempt.phase === "BEFORE" ? "Before class" : attempt.phase === "AFTER" ? "After class" : "During class"} · {attempt.questionCount} questions
                              </td>
                              <td className="px-4 py-3 font-bold text-stone-900">
                                {attempt.submitted ? `${attempt.totalScore}%` : "-"}
                              </td>
                              <td className="px-4 py-3">
                                <span className="rounded-full bg-stone-50 px-3 py-1 text-[11px] font-bold text-stone-700">
                                  {attempt.submitted ? formatReadiness(attempt.readiness) : "Not submitted"}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-stone-500">
                                {formatDateTime(attempt.takenAt)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>

              <section className="rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Next-class readiness loop
                    </h3>
                    <p className="text-xs text-stone-500">
                      Preview the next class, collect quick readiness answers, and publish revision notes.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewActionError("");
                      setIsPreviewModalOpen(true);
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-[#e65100] px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors hover:bg-[#d84315]"
                  >
                    <CalendarPlus size={15} />
                    Prepare next class
                  </button>
                </div>

                {previewActionError && (
                  <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-xs font-semibold text-red-600">
                    {previewActionError}
                  </p>
                )}

                <div className="mt-4 max-h-[520px] space-y-3 overflow-y-auto pr-2">
                  {nextClassReadiness.length > 0 ? (
                    nextClassReadiness.map((preview) => (
                      <div
                        key={preview.id}
                        className="rounded-xl border border-stone-100 bg-stone-50/70 p-4"
                      >
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="text-base font-bold text-stone-900">
                                {preview.title}
                              </p>
                              <span className="rounded-full bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-[#e65100]">
                                {preview.status}
                              </span>
                            </div>
                            <p className="mt-2 max-w-3xl text-xs leading-relaxed text-stone-500">
                              {preview.previewContent || "No preview content yet."}
                            </p>
                            <p className="mt-2 text-[11px] font-semibold text-stone-400">
                              {preview.questions.length} readiness questions
                            </p>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            {preview.status === "DRAFT" && (
                              <button
                                type="button"
                                onClick={() => handlePublishPreview(preview.id)}
                                className="rounded-full border border-stone-900 px-4 py-2 text-xs font-bold text-stone-900 transition-colors hover:bg-white"
                              >
                                Publish
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleAnalyzePreview(preview.id)}
                              className="rounded-full bg-white px-4 py-2 text-xs font-bold text-[#d84315] shadow-sm ring-1 ring-orange-100 transition-colors hover:bg-orange-50"
                            >
                              Analyze
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
                          {preview.summary ? (
                            <>
                              <div className="rounded-xl bg-white p-4 ring-1 ring-stone-100">
                                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                                  Participation
                                </p>
                                <p className="mt-2 text-2xl font-bold text-stone-900">
                                  {preview.summary.participationCount}
                                </p>
                                <p className="mt-1 text-[11px] text-stone-500">
                                  students submitted
                                </p>
                              </div>
                              <div className="rounded-xl bg-white p-4 ring-1 ring-stone-100">
                                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                                  Overall readiness
                                </p>
                                <p className="mt-2 text-2xl font-bold text-stone-900">
                                  {preview.summary.overallReadinessScore}%
                                </p>
                                <p className="mt-1 text-[11px] text-stone-500">
                                  from multiple-choice responses
                                </p>
                              </div>
                              <div className="rounded-xl bg-white p-4 ring-1 ring-stone-100">
                                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                                  Recommendation
                                </p>
                                <p className="mt-2 line-clamp-3 text-xs font-semibold leading-relaxed text-stone-700">
                                  {preview.summary.aiRecommendations[0] ?? "No recommendation yet."}
                                </p>
                              </div>
                            </>
                          ) : (
                            <p className="rounded-xl bg-white p-4 text-xs font-semibold text-stone-500 ring-1 ring-stone-100 lg:col-span-3">
                              No readiness responses analyzed yet.
                            </p>
                          )}
                        </div>

                        {preview.summary && (
                          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
                            <div className="rounded-xl bg-white p-4 ring-1 ring-stone-100">
                              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                                Topic readiness
                              </p>
                              <div className="mt-3 max-h-[210px] space-y-2 overflow-y-auto pr-1">
                                {preview.summary.topicReadiness.map((topic) => (
                                  <div
                                    key={topic.questionId}
                                    className="flex items-center justify-between gap-3 rounded-lg bg-stone-50 px-3 py-2"
                                  >
                                    <div className="min-w-0">
                                      <p className="truncate text-xs font-bold text-stone-800">
                                        {topic.topic}
                                      </p>
                                      <p className="text-[11px] text-stone-500">
                                        {topic.correctResponses}/{topic.totalResponses} correct
                                      </p>
                                    </div>
                                    <span className="text-sm font-bold text-stone-900">
                                      {topic.correctRate}%
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="rounded-xl bg-white p-4 ring-1 ring-stone-100">
                              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                                Revision note
                              </p>
                              <div className="mt-3 space-y-2">
                                <input
                                  value={revisionTopic}
                                  onChange={(event) => setRevisionTopic(event.target.value)}
                                  placeholder="Topic, e.g. Security Group"
                                  className="w-full rounded-xl border border-stone-200 px-3 py-2 text-xs outline-none focus:border-orange-300"
                                />
                                <textarea
                                  value={revisionText}
                                  onChange={(event) => setRevisionText(event.target.value)}
                                  placeholder="What should be reviewed before the next class?"
                                  className="min-h-20 w-full rounded-xl border border-stone-200 px-3 py-2 text-xs outline-none focus:border-orange-300"
                                />
                                <button
                                  type="button"
                                  onClick={() => handleCreateRevision(preview)}
                                  className="rounded-full bg-[#e65100] px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-[#d84315]"
                                >
                                  Save and publish note
                                </button>
                              </div>
                              {preview.summary.revisionNotes.length > 0 && (
                                <div className="mt-3 max-h-[180px] space-y-2 overflow-y-auto pr-1">
                                  {preview.summary.revisionNotes.map((note) => (
                                    <div
                                      key={note.id}
                                      className="rounded-lg bg-orange-50 px-3 py-2 text-xs text-stone-700"
                                    >
                                      <p className="font-bold">{note.topic}</p>
                                      <p className="mt-1">{note.explanation}</p>
                                      <p className="mt-1 text-[10px] font-bold uppercase text-[#d84315]">
                                        {note.isPublished ? "Published to next class" : "Draft"}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="rounded-xl bg-stone-50 p-4 text-sm font-semibold text-stone-500">
                      No next-class readiness preview has been prepared for this session yet.
                    </p>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Most asked topics
                    </h3>
                    <p className="text-xs text-stone-500">
                      Ranked from student chat questions, with captured material references.
                    </p>
                  </div>
                  <Layers size={18} className="text-[#e65100]" />
                </div>

                <div className="mt-4 max-h-[430px] space-y-3 overflow-y-auto pr-2">
                  {summary.topicRanking.length > 0 ? (
                    summary.topicRanking.map((topic, index) => (
                      <div
                        key={topic.topic}
                        className="rounded-xl border border-stone-100 bg-stone-50/70 p-4"
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#fff3ed] text-xs font-bold text-[#e65100]">
                                {index + 1}
                              </span>
                              <p className="text-base font-bold text-stone-900 truncate">
                                {topic.topic}
                              </p>
                            </div>
                            <p className="mt-2 text-xs text-stone-500">
                              Mentioned {topic.count} times across {topic.questionCount} question{topic.questionCount === 1 ? "" : "s"}.
                            </p>
                          </div>

                          <div className="sm:max-w-[52%]">
                            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-stone-400">
                              Material reference
                            </p>
                            {topic.materialRefs.length > 0 ? (
                              <div className="mt-2 flex flex-wrap gap-2">
                                {topic.materialRefs.map((ref) => (
                                  <span
                                    key={`${topic.topic}-${ref.materialId}-${ref.pageNumber ?? "all"}`}
                                    className="rounded-full border border-orange-100 bg-white px-3 py-1 text-[11px] font-semibold text-stone-700"
                                    title={formatMaterialRef(ref)}
                                  >
                                    {ref.fileName}
                                    <span className="ml-1 text-stone-400">
                                      {ref.materialId.slice(0, 8)}
                                      {ref.pageNumber ? ` p.${ref.pageNumber}` : ""}
                                    </span>
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <p className="mt-2 rounded-lg bg-white px-3 py-2 text-[11px] font-semibold text-stone-400">
                                No material reference captured for this topic.
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="rounded-xl bg-stone-50 p-4 text-sm font-semibold text-stone-500">
                      No topic ranking yet.
                    </p>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Answer references
                    </h3>
                    <p className="text-xs text-stone-500">
                      Sources captured for companion answers in this session.
                    </p>
                  </div>
                  <Layers size={18} className="text-[#e65100]" />
                </div>

                <div className="mt-4 max-h-[360px] overflow-auto rounded-xl border border-stone-100">
                  {summary.answerReferences.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[760px] border-collapse bg-white text-left text-xs">
                        <thead className="bg-stone-50 text-[10px] uppercase tracking-[0.16em] text-stone-400">
                          <tr>
                            <th className="px-4 py-3 font-bold">Question</th>
                            <th className="px-4 py-3 font-bold">Source</th>
                            <th className="px-4 py-3 font-bold">Reference</th>
                            <th className="px-4 py-3 font-bold">Evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {summary.answerReferences.map((ref) => (
                            <tr key={ref.id} className="border-t border-stone-100 align-top">
                              <td className="max-w-[240px] px-4 py-3">
                                <p className="font-semibold text-stone-800 line-clamp-2">
                                  {ref.question || "No linked question"}
                                </p>
                                <p className="mt-1 text-[10px] text-stone-400">
                                  {ref.studentName ?? "Student"}
                                </p>
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className={[
                                    "inline-flex rounded-full px-3 py-1 text-[11px] font-bold",
                                    ref.sourceType === "EXTERNAL_AI"
                                      ? "bg-amber-50 text-amber-700"
                                      : "bg-emerald-50 text-emerald-700",
                                  ].join(" ")}
                                >
                                  {ref.sourceType === "EXTERNAL_AI" ? "External AI" : "Material"}
                                </span>
                              </td>
                              <td className="max-w-[220px] px-4 py-3">
                                <p className="font-semibold text-stone-700">
                                  {formatAnswerReference(ref)}
                                </p>
                                {ref.materialId && (
                                  <p className="mt-1 break-all text-[10px] text-stone-400">
                                    {ref.materialId}
                                  </p>
                                )}
                                {ref.provider && (
                                  <p className="mt-1 text-[10px] text-stone-400">
                                    Provider: {ref.provider}
                                  </p>
                                )}
                              </td>
                              <td className="max-w-[280px] px-4 py-3">
                                <p className="line-clamp-3 text-stone-600">
                                  {ref.sourceQuote || "No quote captured."}
                                </p>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="bg-stone-50 p-4 text-sm font-semibold text-stone-500">
                      No answer references captured yet.
                    </p>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Question feed
                    </h3>
                    <p className="text-xs text-stone-500">
                      Questions students asked in this session.
                    </p>
                  </div>
                  <MessageSquareText size={18} className="text-[#e65100]" />
                </div>

                <div className="mt-4 grid max-h-[430px] grid-cols-1 gap-3 overflow-y-auto pr-2 lg:grid-cols-2">
                  {summary.questions.length > 0 ? (
                    summary.questions.map((question) => (
                      <article
                        key={question.id}
                        className="rounded-2xl border border-stone-200/80 bg-stone-50/60 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#fff3ed] text-[11px] font-bold text-[#e65100]">
                              {initials(question.studentName) || "ST"}
                            </span>
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-stone-800 truncate">
                                {question.studentName}
                              </p>
                              <p className="text-[10px] text-stone-400">
                                {formatDateTime(question.createdAt)}
                              </p>
                            </div>
                          </div>
                          {question.imageUrl && (
                            <ImageIcon size={15} className="text-[#e65100]" />
                          )}
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-stone-700">
                          {question.content}
                        </p>
                        {question.materialRefs.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {question.materialRefs.map((ref) => (
                              <span
                                key={`${question.id}-${ref.materialId}-${ref.pageNumber ?? "all"}`}
                                className="rounded-full border border-orange-100 bg-[#fff8f5] px-3 py-1 text-[11px] font-semibold text-stone-700"
                                title={formatMaterialRef(ref)}
                              >
                                Ref: {ref.fileName}
                                <span className="ml-1 text-stone-400">
                                  {ref.materialId.slice(0, 8)}
                                  {ref.pageNumber ? ` p.${ref.pageNumber}` : ""}
                                </span>
                              </span>
                            ))}
                          </div>
                        )}
                        {question.answerReferences.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {question.answerReferences.map((ref) => (
                              <span
                                key={`${question.id}-${ref.id}`}
                                className="rounded-full border border-stone-200 bg-white px-3 py-1 text-[11px] font-semibold text-stone-700"
                                title={formatAnswerReference(ref)}
                              >
                                Answer ref:{" "}
                                {ref.sourceType === "EXTERNAL_AI"
                                  ? "External AI"
                                  : ref.materialFileName ?? ref.materialId?.slice(0, 8) ?? "Material"}
                                {ref.pageNumber ? ` p.${ref.pageNumber}` : ""}
                              </span>
                            ))}
                          </div>
                        )}
                        {question.imageUrl && (
                          <a
                            href={question.imageUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-3 inline-flex text-xs font-bold text-[#d84315] hover:underline"
                          >
                            Open chat image
                          </a>
                        )}
                      </article>
                    ))
                  ) : (
                    <div className="col-span-full rounded-2xl border border-stone-200/80 bg-white/90 p-6 text-sm font-semibold text-stone-500">
                      No student questions yet.
                    </div>
                  )}
                </div>
              </section>

              <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="flex h-[430px] flex-col rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-stone-900">
                        Attendance
                      </h3>
                      <p className="text-xs text-stone-500">
                        Students who checked in with a photo.
                      </p>
                    </div>
                    <Camera size={18} className="text-[#e65100]" />
                  </div>

                  <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-2">
                    {summary.attendances.length > 0 ? (
                      summary.attendances.map((attendance) => (
                        <div
                          key={attendance.id}
                          className="flex items-center gap-3 rounded-xl border border-stone-100 bg-stone-50/70 p-3"
                        >
                          <a
                            href={attendance.photoUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="h-16 w-20 shrink-0 overflow-hidden rounded-lg bg-white border border-stone-200"
                          >
                            <img
                              src={attendance.photoUrl}
                              alt={`${attendance.studentName} attendance`}
                              className="h-full w-full object-cover"
                            />
                          </a>
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-stone-800 truncate">
                              {attendance.studentName}
                            </p>
                            <p className="text-xs text-stone-500">
                              Checked in {formatDateTime(attendance.checkedInAt)}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="rounded-xl bg-stone-50 p-4 text-sm font-semibold text-stone-500">
                        No attendance check-ins yet.
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex h-[430px] flex-col rounded-2xl border border-stone-200/80 bg-white/95 p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-stone-900">
                        Chat image files
                      </h3>
                      <p className="text-xs text-stone-500">
                        Images students attached while asking questions.
                      </p>
                    </div>
                    <ImageIcon size={18} className="text-[#e65100]" />
                  </div>

                  <div className="mt-4 grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto pr-2 sm:grid-cols-2">
                    {summary.chatImages.length > 0 ? (
                      summary.chatImages.map((image) => (
                        <a
                          key={image.id}
                          href={image.imageUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="overflow-hidden rounded-xl border border-stone-200 bg-stone-50 shadow-sm hover:shadow-md transition-shadow"
                        >
                          <img
                            src={image.imageUrl}
                            alt={`${image.studentName} chat attachment`}
                            className="h-28 w-full object-cover"
                          />
                          <div className="p-3">
                            <p className="text-xs font-bold text-stone-800 truncate">
                              {image.studentName}
                            </p>
                            <p className="mt-1 line-clamp-2 text-[11px] text-stone-500">
                              {image.messageContent || "Image attachment"}
                            </p>
                            {image.materialFileName ? (
                              <p className="mt-2 text-[10px] font-semibold text-stone-400">
                                Ref: {image.materialFileName} ({image.materialId?.slice(0, 8)}
                                {image.pageNumber ? ` p.${image.pageNumber}` : ""})
                              </p>
                            ) : (
                              <p className="mt-2 text-[10px] font-semibold text-stone-400">
                                No material reference captured
                              </p>
                            )}
                          </div>
                        </a>
                      ))
                    ) : (
                      <p className="col-span-full rounded-xl bg-stone-50 p-4 text-sm font-semibold text-stone-500">
                        No chat image files yet.
                      </p>
                    )}
                  </div>
                </div>
              </section>
            </>
          ) : (
            <div className="rounded-2xl border border-stone-200/70 bg-white/90 p-6 text-sm font-semibold text-stone-500 shadow-sm">
              {loadError || "Loading from backend..."}
            </div>
          )}
        </div>
      </main>

      {isPreviewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-[1px]">
          <form
            onSubmit={handleCreatePreview}
            className="w-full max-w-[560px] rounded-[26px] border border-stone-100 bg-white p-7 shadow-2xl"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-stone-950">
                  Prepare next class
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-stone-500">
                  Create a short preview and readiness check for the next session.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsPreviewModalOpen(false)}
                className="rounded-md p-1 text-stone-400 transition-colors hover:text-stone-700"
                aria-label="Close next-class preview modal"
              >
                x
              </button>
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="text-xs font-bold text-stone-500">
                  Next session
                </span>
                <select
                  value={nextSessionId}
                  onChange={(event) => setNextSessionId(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-orange-300"
                >
                  <option value="">Choose a session</option>
                  {teacherSessions
                    .filter((session) => session.id !== sessionId)
                    .map((session) => (
                      <option key={session.id} value={session.id}>
                        {session.week} - {session.title}
                      </option>
                    ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-bold text-stone-500">
                  Preview title
                </span>
                <input
                  value={previewTitle}
                  onChange={(event) => setPreviewTitle(event.target.value)}
                  placeholder="Amazon EC2 preview"
                  className="mt-2 w-full rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-orange-300"
                />
              </label>

              <label className="block">
                <span className="text-xs font-bold text-stone-500">
                  Preview content
                </span>
                <textarea
                  value={previewContent}
                  onChange={(event) => setPreviewContent(event.target.value)}
                  placeholder="Short context students should read before answering the readiness check."
                  className="mt-2 min-h-28 w-full rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-orange-300"
                />
              </label>

              {previewActionError && (
                <p className="rounded-xl bg-red-50 px-4 py-3 text-xs font-semibold text-red-600">
                  {previewActionError}
                </p>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setIsPreviewModalOpen(false)}
                className="rounded-full border border-stone-950 px-5 py-2 text-[13px] font-bold text-stone-950 transition-all hover:bg-stone-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPreviewSaving}
                className="rounded-full bg-[#e65100] px-5 py-2 text-[13px] font-bold text-white shadow-sm transition-all hover:bg-[#d84315] disabled:opacity-50"
              >
                {isPreviewSaving ? "Creating..." : "Create preview"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
