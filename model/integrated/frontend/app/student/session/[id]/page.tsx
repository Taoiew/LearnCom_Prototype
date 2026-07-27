"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import {
  Layers,
  FileText,
  TrendingUp,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronDown,
  Send,
  Paperclip,
  X,
  Plus,
  Camera,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import StudentSidebar from "@/components/studentsidebar";
import {
  checkInAttendance,
  getStoredAuthUser,
  getStudentAttendance,
  getStudentChatHistory,
  getSessionDetails,
  sendStudentChatMessage,
  sendStudentChatMessageWithAttachment,
  type ApiSessionResponse,
  type StudentAnswerReference,
} from "@/lib/api";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  image?: string;
  references?: StudentAnswerReference[];
}

const welcomeMessage: Message = {
  id: "welcome",
  sender: "bot",
  text: "Hello. Ask a question about this active session when you are ready.",
};

const DEFAULT_ATTENDANCE_SESSION_DURATION_MINUTES = 180;
const ATTENDANCE_CHECK_IN_WINDOW_SECONDS = 300;

function stableHash(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function formatClock(date: Date) {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(totalSeconds: number) {
  const safeSeconds = Math.max(0, totalSeconds);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function formatReference(ref: StudentAnswerReference) {
  if (ref.sourceType === "EXTERNAL_AI") {
    return ref.sourceName ?? ref.provider ?? "External AI";
  }

  const materialLabel = ref.materialFileName ?? ref.materialId ?? ref.sourceName ?? "Material";
  return `${materialLabel}${ref.pageNumber ? ` p.${ref.pageNumber}` : ""}`;
}

function getScheduledAttendanceAt(
  sessionDate: string,
  sessionId: string,
  studentId: string,
  durationMinutes = DEFAULT_ATTENDANCE_SESSION_DURATION_MINUTES,
) {
  const sessionStart = new Date(sessionDate);
  if (Number.isNaN(sessionStart.getTime())) return null;

  const availableSeconds = Math.max(
    60,
    durationMinutes * 60 - ATTENDANCE_CHECK_IN_WINDOW_SECONDS,
  );
  const offsetSeconds = stableHash(`${sessionId}:${studentId}`) % availableSeconds;
  return new Date(sessionStart.getTime() + offsetSeconds * 1000);
}

export default function Page() {
  const params = useParams();
  const sessionId = params.id as string;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attendanceInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const attendanceScheduleIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [subjectCode, setSubjectCode] = useState("");
  const [currentSession, setCurrentSession] = useState<ApiSessionResponse | null>(null);
  const [loadError, setLoadError] = useState("");
  const [hasCheckedAttendance, setHasCheckedAttendance] = useState(false);
  const [isAttendanceModalOpen, setIsAttendanceModalOpen] = useState(false);
  const [attendanceFile, setAttendanceFile] = useState<File | null>(null);
  const [attendancePreview, setAttendancePreview] = useState<string | null>(null);
  const [attendanceError, setAttendanceError] = useState("");
  const [isCheckingAttendance, setIsCheckingAttendance] = useState(false);
  const [scheduledAttendanceAt, setScheduledAttendanceAt] = useState<Date | null>(null);
  const [attendanceWaitRemaining, setAttendanceWaitRemaining] = useState<number | null>(null);
  const [attendanceCountdownRemaining, setAttendanceCountdownRemaining] = useState<number | null>(null);
  const [isAttendanceWindowExpired, setIsAttendanceWindowExpired] = useState(false);

  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);

  const [inputMessage, setInputMessage] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function loadSessionAndHistory() {
      setIsHistoryLoading(true);
      try {
        const [session, history, attendances] = await Promise.all([
          getSessionDetails(sessionId),
          getStudentChatHistory(sessionId),
          getStudentAttendance(sessionId),
        ]);

        if (ignore) return;

        setCurrentSession(session);
        const isAlreadyCheckedIn = attendances.length > 0;
        setHasCheckedAttendance(isAlreadyCheckedIn);
        if (session.status === "ACTIVE" && !isAlreadyCheckedIn) {
          const user = getStoredAuthUser();
          const assignedTime = user?.id
            ? getScheduledAttendanceAt(
                session.date,
                sessionId,
                user.id,
                session.durationMinutes,
              )
            : null;
          setScheduledAttendanceAt(assignedTime);
        }
        const historyMessages = history.messages.map((message) => ({
          id: message.id,
          sender: message.role === "STUDENT" ? "user" as const : "bot" as const,
          text: message.content,
          image: message.imageUrl ?? undefined,
          references: message.references ?? [],
        }));
        setMessages(historyMessages.length ? historyMessages : [welcomeMessage]);
      } catch (error) {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load session.",
          );
          setMessages([welcomeMessage]);
        }
      } finally {
        if (!ignore) setIsHistoryLoading(false);
      }
    }

    loadSessionAndHistory();

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, isHistoryLoading]);

  useEffect(() => {
    if (hasCheckedAttendance || !scheduledAttendanceAt || attendanceScheduleIntervalRef.current) {
      return;
    }

    const updateSchedule = () => {
      const now = Date.now();
      const checkInStartMs = scheduledAttendanceAt.getTime();
      const checkInEndMs = checkInStartMs + ATTENDANCE_CHECK_IN_WINDOW_SECONDS * 1000;

      if (now < checkInStartMs) {
        setAttendanceWaitRemaining(Math.ceil((checkInStartMs - now) / 1000));
        setAttendanceCountdownRemaining(null);
        return;
      }

      if (now <= checkInEndMs) {
        setAttendanceWaitRemaining(null);
        setAttendanceCountdownRemaining(Math.ceil((checkInEndMs - now) / 1000));
        setIsAttendanceModalOpen(true);
        return;
      }

      setAttendanceWaitRemaining(null);
      setAttendanceCountdownRemaining(null);
      setIsAttendanceWindowExpired(true);
      setIsAttendanceModalOpen(false);
      clearAttendancePhoto();
      if (attendanceScheduleIntervalRef.current) {
        clearInterval(attendanceScheduleIntervalRef.current);
        attendanceScheduleIntervalRef.current = null;
      }
    };

    updateSchedule();
    attendanceScheduleIntervalRef.current = setInterval(updateSchedule, 1000);

    return () => {
      if (attendanceScheduleIntervalRef.current) {
        clearInterval(attendanceScheduleIntervalRef.current);
        attendanceScheduleIntervalRef.current = null;
      }
    };
  }, [scheduledAttendanceAt, hasCheckedAttendance]);

  const handleAddSubjectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`Adding subject with code: ${subjectCode}`);
    setIsAddSubjectModalOpen(false);
    setSubjectCode("");
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const messageText = inputMessage.trim();
    const attachedFile = selectedFile;
    const attachedPreview = selectedImage;
    if ((!messageText && !attachedFile) || isSending) return;

    const userMessageId = `local-user-${Date.now()}`;
    const pendingMessageId = `local-bot-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        sender: "user",
        text: messageText,
        image: attachedPreview || undefined,
      },
      {
        id: pendingMessageId,
        sender: "bot",
        text: "Thinking...",
      },
    ]);

    setInputMessage("");
    setSelectedImage(null);
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    setIsSending(true);
    let reply = "";
    let replyReferences: StudentAnswerReference[] = [];
    try {
      if (attachedFile) {
        const result = await sendStudentChatMessageWithAttachment({
          sessionId,
          message: messageText || "Please review the attached file.",
          file: attachedFile,
        });
        reply = result.response;
        replyReferences = result.references;
      } else {
        const result = await sendStudentChatMessage({
          sessionId,
          message: messageText,
        });
        reply = result.response;
        replyReferences = result.references;
      }
    } catch (error) {
      reply =
        error instanceof Error
          ? `The learning companion could not answer: ${error.message}`
          : "The learning companion could not answer.";
    }

    setMessages((prev) =>
      prev.map((message) =>
        message.id === pendingMessageId
          ? { ...message, text: reply, references: replyReferences }
          : message,
      ),
    );
    setIsSending(false);
  };

  const handleAttendanceImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAttendanceError("");
    setAttendanceFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setAttendancePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const clearAttendancePhoto = () => {
    setAttendanceFile(null);
    setAttendancePreview(null);
    if (attendanceInputRef.current) {
      attendanceInputRef.current.value = "";
    }
  };

  const handleAttendanceCheckIn = async () => {
    if (!attendanceFile || isCheckingAttendance) {
      setAttendanceError("Please add a photo before checking in.");
      return;
    }

    setAttendanceError("");
    setIsCheckingAttendance(true);
    try {
      await checkInAttendance({
        sessionId,
        file: attendanceFile,
      });
      setHasCheckedAttendance(true);
      setAttendanceCountdownRemaining(null);
      setAttendanceWaitRemaining(null);
      setScheduledAttendanceAt(null);
      setIsAttendanceModalOpen(false);
      clearAttendancePhoto();
    } catch (error) {
      setAttendanceError(
        error instanceof Error ? error.message : "Could not check attendance.",
      );
    } finally {
      setIsCheckingAttendance(false);
    }
  };

  const weekTitle = "Active session";
  const sessionTitle = currentSession?.title || "Loading session";
  const description =
    currentSession?.description ||
    loadError ||
    "Ask questions before class. Your gaps carry over to a short quiz.";
  const attendanceButtonLabel = hasCheckedAttendance
    ? "Checked in"
    : attendanceCountdownRemaining !== null
      ? `Check in ${formatDuration(attendanceCountdownRemaining)}`
      : attendanceWaitRemaining !== null
        ? `Opens in ${formatDuration(attendanceWaitRemaining)}`
        : isAttendanceWindowExpired
          ? "Attendance closed"
          : "Check attendance";
  const canOpenAttendanceModal =
    !hasCheckedAttendance &&
    !isAttendanceWindowExpired &&
    attendanceCountdownRemaining !== null;

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <StudentSidebar />

      {/* RIGHT MAIN CONTENT */}
      <main
        className="flex-1 pl-64 px-8 pt-12 pb-8 relative overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-5">
          {/* Header & Back Button */}
          <div>
            <button
              suppressHydrationWarning
              onClick={() => window.history.back()}
              className="inline-flex items-center gap-1 text-xs font-semibold text-stone-500 hover:text-stone-800 mb-3 transition-colors cursor-pointer"
            >
              <ChevronLeft size={16} /> Your sessions
            </button>

            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
                  {weekTitle} - {sessionTitle}
                </h2>
                <p className="text-xs text-stone-400 mt-1">{description}</p>
              </div>

              <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
                <button
                  suppressHydrationWarning
                  type="button"
                  onClick={() => {
                    if (canOpenAttendanceModal) setIsAttendanceModalOpen(true);
                  }}
                  disabled={!hasCheckedAttendance && !canOpenAttendanceModal}
                  className={`inline-flex items-center gap-2 px-5 py-4 text-[13px] font-bold rounded-full shadow-sm hover:shadow transition-all active:scale-95 cursor-pointer flex-shrink-0 ${
                    hasCheckedAttendance
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                      : canOpenAttendanceModal
                        ? "bg-white text-[#d84315] border border-orange-100"
                        : "bg-white/70 text-stone-400 border border-stone-200 cursor-not-allowed"
                  }`}
                >
                  {hasCheckedAttendance ? <CheckCircle2 size={15} /> : <Camera size={15} />}
                  {attendanceButtonLabel}
                </button>
                <button
                  suppressHydrationWarning
                  onClick={() =>
                    window.location.assign(`/student/session/${sessionId}/quiz`)
                  }
                  className="px-6 py-4 bg-[#e65100] hover:bg-[#d84315] text-white text-[13px] font-bold rounded-full shadow-sm hover:shadow transition-all active:scale-95 cursor-pointer flex-shrink-0"
                >
                  Take readiness quiz
                </button>
              </div>
            </div>
          </div>

          {/* Chat Card Box */}
          <div className="bg-white border border-stone-200/80 rounded-2xl p-6 md:p-8 shadow-sm flex min-h-0 h-[calc(100vh-190px)] min-h-[520px] flex-col justify-between">
            {/* Header inside chat */}
            <div className="flex items-center justify-between pb-4 border-b border-stone-100">
              <h2 className="text-sm md:text-base font-bold text-stone-800">
                Ask the companion
              </h2>
              <span className="px-3 py-1 bg-[#fff3ed] text-[#d84315] rounded-full text-xs font-semibold border border-orange-100">
                Active
              </span>
            </div>

            {/* Messages list */}
            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain py-6 pr-2">
              {isHistoryLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] md:max-w-[70%] text-xs md:text-sm leading-relaxed px-5 py-3.5 rounded-2xl bg-[#e8e5df] text-stone-500 rounded-tl-xs font-normal">
                    Loading chat history...
                  </div>
                </div>
              )}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.sender === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] md:max-w-[70%] text-xs md:text-sm leading-relaxed px-5 py-3.5 rounded-2xl ${
                      msg.sender === "user"
                        ? "bg-[#d84315] text-white rounded-tr-xs font-normal shadow-sm"
                        : "bg-[#e8e5df] text-stone-800 rounded-tl-xs font-normal"
                    }`}
                  >
                    {msg.image && (
                      <img
                        src={msg.image}
                        alt="attachment"
                        className="max-h-48 rounded-xl mb-2.5 object-cover border border-black/10"
                      />
                    )}
                    {msg.text && <p className="whitespace-pre-wrap">{msg.text}</p>}
                    {msg.sender === "bot" && msg.references && msg.references.length > 0 && (
                      <div className="mt-3 overflow-hidden rounded-xl border border-stone-300/60 bg-white/70 text-stone-800">
                        <div className="grid grid-cols-[110px_1fr] border-b border-stone-200/70 bg-stone-50/80 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.12em] text-stone-400">
                          <span>Source</span>
                          <span>Reference</span>
                        </div>
                        {msg.references.map((ref, index) => (
                          <div
                            key={`${msg.id}-ref-${ref.id ?? index}`}
                            className="grid grid-cols-[110px_1fr] gap-2 border-b border-stone-100 px-3 py-2 last:border-b-0"
                          >
                            <span
                              className={[
                                "w-fit rounded-full px-2 py-0.5 text-[10px] font-bold",
                                ref.sourceType === "EXTERNAL_AI"
                                  ? "bg-amber-50 text-amber-700"
                                  : "bg-emerald-50 text-emerald-700",
                              ].join(" ")}
                            >
                              {ref.sourceType === "EXTERNAL_AI" ? "External AI" : "Material"}
                            </span>
                            <span className="min-w-0 text-[11px] font-semibold text-stone-700">
                              {formatReference(ref)}
                              {ref.sourceQuote && (
                                <span className="mt-1 block line-clamp-2 font-normal text-stone-500">
                                  {ref.sourceQuote}
                                </span>
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <form
              onSubmit={handleSend}
              className="relative flex flex-col gap-2 pt-2"
            >
              {selectedImage && (
                <div className="relative inline-block w-20 h-20 rounded-xl overflow-hidden border border-stone-300 shadow-sm ml-2">
                  <img
                    src={selectedImage}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                  <button
                    suppressHydrationWarning
                  type="button"
                  onClick={() => {
                    setSelectedImage(null);
                    setSelectedFile(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = "";
                    }
                  }}
                    className="absolute top-1 right-1 p-0.5 bg-stone-900/70 hover:bg-stone-900 text-white rounded-full transition-colors cursor-pointer"
                  >
                    <X size={12} />
                  </button>
                </div>
              )}

              <div className="relative flex items-center w-full">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleImageSelect}
                  accept="image/*"
                  className="hidden"
                />

                <button
                  suppressHydrationWarning
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute left-3.5 text-stone-400 hover:text-[#d84315] transition-colors p-1 rounded-full cursor-pointer"
                  title="Attach image"
                >
                  <Paperclip size={18} />
                </button>

                <input
                  suppressHydrationWarning
                  type="text"
                  placeholder={
                    isSending
                      ? "Waiting for the companion..."
                      : "Ask about EC2, IAM, or this week's material"
                  }
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  disabled={isSending}
                  className="w-full pl-12 pr-14 py-3.5 bg-[#e8e5df]/60 focus:bg-[#e8e5df] text-xs md:text-sm text-stone-800 placeholder-stone-400 rounded-full outline-none transition-all"
                />

                <button
                  suppressHydrationWarning
                  type="submit"
                  disabled={isSending}
                  className="absolute right-2 w-9 h-9 bg-[#f48c5a] hover:bg-[#e65100] text-white rounded-full flex items-center justify-center transition-all cursor-pointer shadow-sm"
                >
                  <Send size={15} className="ml-0.5" />
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>

      {isAttendanceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-[1px]">
          <div className="w-full max-w-[440px] rounded-[26px] border border-stone-100 bg-white p-7 text-left shadow-2xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-stone-950">
                  Attendance check-in
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-stone-500">
                  Your check-in slot is
                  {scheduledAttendanceAt ? ` ${formatClock(scheduledAttendanceAt)}` : ""}.
                  Upload a photo before the countdown ends. The photo will be
                  stored without AI verification.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsAttendanceModalOpen(false)}
                className="rounded-md p-1 text-stone-400 transition-colors hover:text-stone-700"
                aria-label="Close attendance check-in"
              >
                <X size={18} />
              </button>
            </div>

            {attendanceCountdownRemaining !== null && (
              <div className="mb-4 rounded-2xl bg-orange-50 px-4 py-3 text-center ring-1 ring-orange-100">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#d84315]">
                  Time left to check in
                </p>
                <p className="mt-1 text-3xl font-bold text-stone-950">
                  {attendanceCountdownRemaining}s
                </p>
              </div>
            )}

            <input
              ref={attendanceInputRef}
              type="file"
              accept="image/*"
              capture="user"
              onChange={handleAttendanceImageSelect}
              className="hidden"
            />

            <button
              type="button"
              onClick={() => attendanceInputRef.current?.click()}
              disabled={attendanceCountdownRemaining === null}
              className="flex min-h-[190px] w-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-stone-300 bg-stone-50/70 p-4 text-center transition-colors hover:border-orange-300 hover:bg-orange-50/40"
            >
              {attendancePreview ? (
                <img
                  src={attendancePreview}
                  alt="Attendance preview"
                  className="max-h-48 rounded-xl object-cover"
                />
              ) : (
                <>
                  <span className="flex h-12 w-12 items-center justify-center rounded-full bg-orange-50 text-[#d84315]">
                    <Camera size={22} />
                  </span>
                  <span className="text-sm font-bold text-stone-800">
                    Add attendance photo
                  </span>
                  <span className="text-xs text-stone-400">
                    Camera or image upload
                  </span>
                </>
              )}
            </button>

            {attendancePreview && (
              <button
                type="button"
                onClick={clearAttendancePhoto}
                className="mt-3 text-xs font-bold text-stone-400 hover:text-stone-700"
              >
                Remove photo
              </button>
            )}

            {attendanceError && (
              <p className="mt-4 text-xs font-semibold text-red-500">
                {attendanceError}
              </p>
            )}

            <div className="mt-6 flex justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setIsAttendanceModalOpen(false)}
                className="rounded-full border border-stone-950 px-5 py-2 text-[13px] font-bold text-stone-950 transition-all hover:bg-stone-50"
              >
                Later
              </button>
              <button
                type="button"
                onClick={handleAttendanceCheckIn}
                disabled={isCheckingAttendance || !attendanceFile}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#e65100] px-5 py-2 text-[13px] font-bold text-white shadow-sm transition-all hover:bg-[#d84315] disabled:opacity-50"
              >
                {isCheckingAttendance && <Loader2 size={14} className="animate-spin" />}
                Check in
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
