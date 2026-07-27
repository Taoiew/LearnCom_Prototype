export type Role = "teacher" | "student";

export interface ApiUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  token: string;
}

export interface AppSubject {
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
}

export interface ApiMaterial {
  id: string;
  fileName: string;
  fileUrl: string;
  fileType: string;
  isProcessed: boolean;
  uploadedAt: string;
}

export interface ApiSessionResponse {
  id: string;
  subjectId?: string;
  title: string;
  status: "UPCOMING" | "ACTIVE" | "COMPLETED";
  phase: "BEFORE" | "DURING" | "AFTER";
  date: string;
  durationMinutes?: number;
  description?: string | null;
  readinessPercent?: number;
  subject?: { name?: string };
  materials?: ApiMaterial[];
  _count?: {
    materials?: number;
    sessionCriteria?: number;
  };
}

export interface ApiAttendance {
  id: string;
  studentId: string;
  sessionId: string;
  photoUrl: string;
  checkedInAt: string;
  session?: {
    id: string;
    title: string;
    date: string;
    status: ApiSessionResponse["status"];
    subject?: { name?: string };
  };
}

export interface ApiSubjectResponse {
  id: string;
  name: string;
  description?: string | null;
  teacherId?: string;
  sessions?: ApiSessionResponse[];
  _count?: {
    sessions?: number;
    semesterCriteria?: number;
  };
}

export interface TeacherSession {
  id: string;
  week: string;
  title: string;
  status: "Completed" | "Active" | "Upcoming";
  segments: string[];
  avgReadiness: string;
  isLive?: boolean;
  date?: string;
  startTime?: string;
  endTime?: string;
}

export interface TeacherDashboardViewModel {
  subjects: AppSubject[];
  sessionsBySubject: Record<string, TeacherSession[]>;
}

export interface StudentSession {
  id: string;
  week: string;
  title: string;
  description: string;
  status: "Completed" | "Active" | "Upcoming";
  date: string;
  info: string;
  attendance?: {
    isPresent: boolean;
    checkedInAt?: string;
    photoUrl?: string;
  };
}

export interface StudentDashboardViewModel {
  subjects: AppSubject[];
  sessionsBySubject: Record<string, StudentSession[]>;
  attendance: {
    presentCount: number;
    totalActiveSessions: number;
    latest?: ApiAttendance;
  };
}

export interface StudentMaterialsViewModel {
  subjectCode: string;
  groups: Array<{
    weekTitle: string;
    items: Array<{
      id: string;
      title: string;
      type: string;
      size: string;
      updatedAt: string;
      downloadUrl: string;
    }>;
  }>;
}

export interface StudentProgressViewModel {
  subjectCode: string;
  stats: Array<{
    label: string;
    value: string;
    subtext: string;
  }>;
  progress: Array<{
    id: string;
    weekTitle: string;
    status: string;
    percentage: number;
    color: string;
  }>;
}

export interface StudentChatHistoryMessage {
  id: string;
  role: "STUDENT" | "AGENT";
  content: string;
  createdAt: string;
  imageUrl?: string | null;
  references?: StudentAnswerReference[];
}

export interface StudentChatHistory {
  conversationId: string | null;
  phase: string;
  messages: StudentChatHistoryMessage[];
  summary: string;
}

export interface StudentAnswerReference {
  id?: string;
  messageId?: string;
  studentMessageId?: string | null;
  sourceType: "MATERIAL" | "EXTERNAL_AI";
  sourceName: string | null;
  materialId: string | null;
  materialFileName: string | null;
  pageNumber: number | null;
  sourceQuote: string | null;
  provider: string | null;
  createdAt?: string;
}

export interface StudentChatResponse {
  response: string;
  references: StudentAnswerReference[];
}

export interface TeacherSessionSummary {
  session: {
    id: string;
    title: string;
    status: ApiSessionResponse["status"];
    phase: ApiSessionResponse["phase"];
    date: string;
    durationMinutes: number;
    subject: { id: string; name: string };
  };
  stats: {
    studentsAttended: number;
    questionsAsked: number;
    chatImagesSent: number;
    attendancePhotos: number;
    topTopic: string;
  };
  questions: Array<{
    id: string;
    studentId: string;
    studentName: string;
    content: string;
    createdAt: string;
    imageUrl?: string | null;
    answerReferences: TeacherAnswerReference[];
    materialRefs: Array<{
      materialId: string;
      fileName: string;
      pageNumber: number | null;
    }>;
  }>;
  attendances: Array<{
    id: string;
    studentId: string;
    studentName: string;
    photoUrl: string;
    checkedInAt: string;
  }>;
  chatImages: Array<{
    id: string;
    studentId: string;
    studentName: string;
    imageUrl: string;
    materialId: string | null;
    materialFileName: string | null;
    pageNumber: number | null;
    messageId: string;
    messageContent: string;
    createdAt: string;
  }>;
  topicRanking: Array<{
    topic: string;
    count: number;
    questionCount: number;
    materialRefs: Array<{
      materialId: string;
      fileName: string;
      pageNumber: number | null;
    }>;
  }>;
  quizOverview: {
    totalAttempts: number;
    submittedAttempts: number;
    averageScore: number;
    studentsSubmitted: number;
    studentsPassed: number;
    phases: Array<{
      phase: "BEFORE" | "AFTER";
      attempts: number;
      submittedAttempts: number;
      studentsSubmitted: number;
      averageScore: number;
      readyCount: number;
      partialCount: number;
      notReadyCount: number;
    }>;
    criteriaBreakdown: Array<{
      criteriaId: string;
      description: string;
      metCount: number;
      partialCount: number;
      notMetCount: number;
    }>;
    recentAttempts: Array<{
      quizId: string;
      studentId: string;
      studentName: string;
      phase: "BEFORE" | "DURING" | "AFTER";
      submitted: boolean;
      totalScore: number;
      readiness: "READY" | "PARTIAL" | "NOT_READY";
      questionCount: number;
      takenAt: string;
    }>;
  };
  answerReferences: TeacherAnswerReference[];
}

export interface TeacherAnswerReference {
  id: string;
  messageId: string;
  studentMessageId: string | null;
  studentId?: string;
  studentName?: string;
  question?: string;
  sourceType: "MATERIAL" | "EXTERNAL_AI";
  sourceName: string | null;
  materialId: string | null;
  materialFileName: string | null;
  pageNumber: number | null;
  sourceQuote: string | null;
  provider: string | null;
  createdAt: string;
}

export interface ReadinessQuizQuestion {
  id: string;
  criteriaId: string;
  order: number;
  questionText: string;
  questionType: string;
  options: unknown;
  rubric: {
    description: string;
    goal: string;
  };
  sourceExcerpt: string;
}

export type QuizPhase = "BEFORE" | "AFTER";

export interface GeneratedReadinessQuiz {
  quizId: string;
  phase: QuizPhase;
  questions: ReadinessQuizQuestion[];
}

export interface SubmittedQuizResult {
  quizId: string;
  totalScore: number;
  readiness: "READY" | "PARTIAL" | "NOT_READY";
  criteriaResults: Array<{
    criteriaId: string;
    description: string;
    status: "MET" | "PARTIAL" | "NOT_MET";
    feedback: string;
  }>;
  weakCriteria: string[];
  recommendation: string;
}

const AUTH_STORAGE_KEY = "learning-companion-auth";
export const TEACHER_SUBJECT_STORAGE_KEY = "learning-companion-teacher-subject";
export const TEACHER_SUBJECT_CHANGE_EVENT =
  "learning-companion-teacher-subject-change";

function normalizeRole(role: unknown): Role {
  return String(role).toLowerCase() === "teacher" ? "teacher" : "student";
}

function getAuthHeaders(): HeadersInit {
  const user = getStoredAuthUser();
  if (!user?.token) {
    throw new Error("Please log in with a real backend account first.");
  }

  return { Authorization: `Bearer ${user.token}` };
}

async function parseError(response: Response, fallback: string) {
  try {
    const body = await response.json();
    return body.error ?? body.detail ?? fallback;
  } catch {
    return (await response.text()) || fallback;
  }
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...getAuthHeaders(),
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const message = await parseError(response, `Request failed: ${response.status}`);
    if (response.status === 401) {
      clearAuthUser();
      if (typeof window !== "undefined") {
        window.location.assign("/login");
      }
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function splitSubjectName(subject: ApiSubjectResponse) {
  const rawName = subject.name.trim();
  const match = rawName.match(/^([A-Za-z]{2,}\d{2,})\s*[-:]\s*(.+)$/);
  const code = match?.[1] ?? rawName;
  const name = match?.[2] ?? rawName;
  return { code, name };
}

function mapSubject(subject: ApiSubjectResponse): AppSubject {
  const { code, name } = splitSubjectName(subject);
  const sessionsRun = subject._count?.sessions ?? subject.sessions?.length ?? 0;

  return {
    id: subject.id,
    code,
    name,
    displayShort: code === name ? name : `${code} - ${name}`,
    subtitle: subject.description ?? "",
    weeks: `${sessionsRun} sessions`,
    stats: {
      avgReadiness: "0%",
      semesterProgress: "0%",
      progressCriteria: "Based on real backend sessions",
      sessionsRun,
      studentsCaughtUp: "0%",
    },
  };
}

function mapSessionStatus(
  status: ApiSessionResponse["status"],
): "Completed" | "Active" | "Upcoming" {
  if (status === "COMPLETED") return "Completed";
  if (status === "ACTIVE") return "Active";
  return "Upcoming";
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatTime(date: string) {
  return new Date(date).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatEndTime(date: string, durationMinutes = 180) {
  const start = new Date(date);
  const end = new Date(start.getTime() + durationMinutes * 60 * 1000);
  return end.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function mapTeacherSession(session: ApiSessionResponse, index: number): TeacherSession {
  const status = mapSessionStatus(session.status);
  return {
    id: session.id,
    week: `Session ${index + 1}`,
    title: session.title,
    status,
    segments: ["bg-stone-200", "bg-stone-200", "bg-stone-200", "bg-stone-200"],
    avgReadiness: `${session.readinessPercent ?? 0}%`,
    isLive: status === "Active",
    date: formatDate(session.date),
    startTime: formatTime(session.date),
    endTime: formatEndTime(session.date, session.durationMinutes),
  };
}

function mapStudentSession(session: ApiSessionResponse, index: number): StudentSession {
  const status = mapSessionStatus(session.status);
  return {
    id: session.id,
    week: `Session ${index + 1}`,
    title: session.title,
    description: session.description ?? "",
    status,
    date: formatDate(session.date),
    info:
      session.phase === "BEFORE"
        ? "Before class"
        : session.phase === "DURING"
          ? "Live now"
          : "Ready",
  };
}

export async function loginWithBackend(
  email: string,
  password: string,
): Promise<ApiUser> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response, "Invalid email or password."));
  }

  const body = await response.json();
  return {
    id: body.user?.id ?? body.id,
    name: body.user?.name ?? body.name ?? email,
    email: body.user?.email ?? body.email ?? email,
    role: normalizeRole(body.user?.role ?? body.role),
    token: body.token,
  };
}

export function getStoredAuthUser(): ApiUser | null {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as ApiUser;
  } catch {
    return null;
  }
}

export function persistAuthUser(user: ApiUser): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
}

export function clearAuthUser(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function getStoredTeacherSubjectId(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TEACHER_SUBJECT_STORAGE_KEY) ?? "";
}

export function persistTeacherSubjectId(subjectId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TEACHER_SUBJECT_STORAGE_KEY, subjectId);
  window.dispatchEvent(
    new CustomEvent(TEACHER_SUBJECT_CHANGE_EVENT, { detail: subjectId }),
  );
}

export async function getSubjects(role: Role): Promise<AppSubject[]> {
  if (role === "teacher") {
    const body = await apiFetch<{ subjects: ApiSubjectResponse[] }>("/api/v1/subjects");
    return body.subjects.map(mapSubject);
  }

  const viewModel = await getStudentDashboardViewModel();
  return viewModel.subjects;
}

export async function getTeacherDashboardViewModel(): Promise<TeacherDashboardViewModel> {
  const [subjectsBody, sessionsBody] = await Promise.all([
    apiFetch<{ subjects: ApiSubjectResponse[] }>("/api/v1/subjects"),
    apiFetch<{ sessions: ApiSessionResponse[] }>("/api/v1/sessions"),
  ]);

  const subjects = subjectsBody.subjects.map(mapSubject);
  const sessionsBySubject: TeacherDashboardViewModel["sessionsBySubject"] = {};

  for (const subject of subjects) {
    sessionsBySubject[subject.code] = [];
  }

  for (const session of sessionsBody.sessions) {
    const subject = subjects.find((item) => item.id === session.subjectId);
    const key = subject?.code ?? session.subject?.name ?? "Unassigned";
    const list = sessionsBySubject[key] ?? [];
    list.push(mapTeacherSession(session, list.length));
    sessionsBySubject[key] = list;
  }

  return { subjects, sessionsBySubject };
}

export async function getStudentDashboardViewModel(): Promise<StudentDashboardViewModel> {
  const [body, attendanceBody] = await Promise.all([
    apiFetch<{ sessions: ApiSessionResponse[] }>("/api/v1/sessions"),
    apiFetch<{ attendances: ApiAttendance[] }>("/api/v1/attendance"),
  ]);
  const subjectsByName = new Map<string, AppSubject>();
  const sessionsBySubject: StudentDashboardViewModel["sessionsBySubject"] = {};
  const attendanceBySessionId = new Map(
    attendanceBody.attendances.map((attendance) => [attendance.sessionId, attendance]),
  );

  for (const session of body.sessions) {
    const subjectName = session.subject?.name ?? "Active course";
    const pseudoSubject: ApiSubjectResponse = {
      id: session.subjectId ?? subjectName,
      name: subjectName,
      description: "",
      _count: { sessions: 0, semesterCriteria: 0 },
    };
    const subject = subjectsByName.get(subjectName) ?? mapSubject(pseudoSubject);
    subjectsByName.set(subjectName, {
      ...subject,
      weeks: `${(sessionsBySubject[subject.code]?.length ?? 0) + 1} sessions`,
    });

    const list = sessionsBySubject[subject.code] ?? [];
    const attendance = attendanceBySessionId.get(session.id);
    list.push({
      ...mapStudentSession(session, list.length),
      attendance: {
        isPresent: Boolean(attendance),
        checkedInAt: attendance?.checkedInAt,
        photoUrl: attendance?.photoUrl,
      },
    });
    sessionsBySubject[subject.code] = list;
  }

  return {
    subjects: Array.from(subjectsByName.values()),
    sessionsBySubject,
    attendance: {
      presentCount: attendanceBody.attendances.length,
      totalActiveSessions: body.sessions.length,
      latest: attendanceBody.attendances[0],
    },
  };
}

export async function getStudentMaterialsViewModel(
  subjectCode = "",
): Promise<StudentMaterialsViewModel> {
  const dashboard = await getStudentDashboardViewModel();
  const sessions = dashboard.sessionsBySubject[subjectCode] ?? [];
  const groups: StudentMaterialsViewModel["groups"] = [];

  for (const session of sessions) {
    const body = await apiFetch<{ materials: ApiMaterial[] }>(
      `/api/v1/sessions/${session.id}/materials`,
    );
    if (body.materials.length === 0) continue;

    groups.push({
      weekTitle: `${session.week} - ${session.title}`,
      items: body.materials.map((material) => ({
        id: material.id,
        title: material.fileName,
        type: material.fileType.split("/").pop()?.toUpperCase() ?? "FILE",
        size: "Uploaded file",
        updatedAt: `updated ${formatDate(material.uploadedAt)}`,
        downloadUrl: material.fileUrl,
      })),
    });
  }

  return { subjectCode, groups };
}

export async function getStudentProgressViewModel(
  subjectCode = "",
): Promise<StudentProgressViewModel> {
  const dashboard = await getStudentDashboardViewModel();
  const sessions = dashboard.sessionsBySubject[subjectCode] ?? [];
  const completedCount = sessions.filter((session) => session.status === "Completed").length;

  return {
    subjectCode,
    stats: [
      { label: "Avg readiness", value: "0%", subtext: "from real reports" },
      {
        label: "Sessions done",
        value: `${completedCount} / ${sessions.length}`,
        subtext: "this semester",
      },
      { label: "Active sessions", value: `${sessions.filter((s) => s.status === "Active").length}`, subtext: "available now" },
    ],
    progress: sessions.map((session) => ({
      id: session.id,
      weekTitle: `${session.week} - ${session.title}`,
      status: session.status,
      percentage: session.status === "Completed" ? 100 : 0,
      color:
        session.status === "Completed"
          ? "bg-emerald-500"
          : session.status === "Active"
            ? "bg-[#e65100]"
            : "bg-stone-200",
    })),
  };
}

export async function createSubject(
  role: Role,
  payload: { code: string; name: string },
): Promise<AppSubject> {
  if (role !== "teacher") {
    throw new Error("Only teachers can create subjects.");
  }

  const name = payload.code.trim()
    ? `${payload.code.trim()} - ${payload.name.trim()}`
    : payload.name.trim();

  const body = await apiFetch<{ subject: ApiSubjectResponse }>("/api/v1/subjects", {
    method: "POST",
    body: JSON.stringify({ name, description: "" }),
  });

  return mapSubject({ ...body.subject, _count: { sessions: 0, semesterCriteria: 0 } });
}

export async function createSession(payload: {
  title: string;
  week?: string;
  date: string;
  durationMinutes?: number;
  description?: string;
  subjectId?: string;
}): Promise<{ id: string; title: string; week: string; date: string }> {
  if (!payload.subjectId) {
    throw new Error("Choose or create a real subject before creating a session.");
  }

  const body = await apiFetch<{ session: ApiSessionResponse }>("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify({
      subjectId: payload.subjectId,
      title: payload.title,
      description: payload.description ?? "",
      date: payload.date,
      durationMinutes: payload.durationMinutes ?? 180,
    }),
  });

  return {
    id: body.session.id,
    title: body.session.title,
    week: payload.week ?? "New session",
    date: body.session.date,
  };
}

export async function startSession(sessionId: string): Promise<ApiSessionResponse> {
  const body = await apiFetch<{ session: ApiSessionResponse }>(
    `/api/v1/sessions/${sessionId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status: "ACTIVE", phase: "BEFORE" }),
    },
  );

  return body.session;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch<{ success: boolean }>(`/api/v1/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export async function uploadMaterialsForSession(files: File[], sessionId?: string): Promise<void> {
  if (!sessionId) {
    throw new Error("Choose a real session before uploading materials.");
  }

  for (const file of files) {
    const formData = new FormData();
    formData.append("file", file);

    await apiFetch(`/api/v1/sessions/${sessionId}/materials`, {
      method: "POST",
      body: formData,
    });
  }
}

export async function sendStudentChatMessage(payload: {
  sessionId: string;
  message: string;
}): Promise<StudentChatResponse> {
  const user = getStoredAuthUser();
  if (user?.role !== "student") {
    throw new Error("Please log in as a student before using the companion chat.");
  }

  const body = await apiFetch<{ response?: string; references?: StudentAnswerReference[] }>("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify({
      sessionId: payload.sessionId,
      message: payload.message,
    }),
  });

  if (!body.response) {
    throw new Error("The model returned an empty response.");
  }

  return { response: body.response, references: body.references ?? [] };
}

export async function sendStudentChatMessageWithAttachment(payload: {
  sessionId: string;
  message: string;
  file: File;
}): Promise<StudentChatResponse> {
  const user = getStoredAuthUser();
  if (user?.role !== "student") {
    throw new Error("Please log in as a student before using the companion chat.");
  }

  const formData = new FormData();
  formData.append("sessionId", payload.sessionId);
  formData.append("message", payload.message);
  formData.append("file", payload.file, payload.file.name);

  const body = await apiFetch<{ response?: string; references?: StudentAnswerReference[] }>("/api/v1/chat/upload", {
    method: "POST",
    body: formData,
  });

  if (!body.response) {
    throw new Error("The model returned an empty response.");
  }

  return { response: body.response, references: body.references ?? [] };
}

export async function getStudentChatHistory(
  sessionId: string,
): Promise<StudentChatHistory> {
  const user = getStoredAuthUser();
  if (user?.role !== "student") {
    throw new Error("Please log in as a student before using the companion chat.");
  }

  return apiFetch<StudentChatHistory>(`/api/v1/chat/history/${sessionId}`);
}

export async function getStudentAttendance(
  sessionId?: string,
): Promise<ApiAttendance[]> {
  const query = sessionId ? `?sessionId=${encodeURIComponent(sessionId)}` : "";
  const body = await apiFetch<{ attendances: ApiAttendance[] }>(
    `/api/v1/attendance${query}`,
  );
  return body.attendances;
}

export async function checkInAttendance(payload: {
  sessionId: string;
  file: File;
}): Promise<ApiAttendance> {
  const user = getStoredAuthUser();
  if (user?.role !== "student") {
    throw new Error("Please log in as a student before checking attendance.");
  }

  const formData = new FormData();
  formData.append("sessionId", payload.sessionId);
  formData.append("file", payload.file, payload.file.name);

  const body = await apiFetch<{ attendance: ApiAttendance }>("/api/v1/attendance", {
    method: "POST",
    body: formData,
  });

  return body.attendance;
}

export async function getSessionDetails(sessionId: string): Promise<ApiSessionResponse> {
  const body = await apiFetch<{ session: ApiSessionResponse }>(
    `/api/v1/sessions/${sessionId}`,
  );
  return body.session;
}

export async function getTeacherSessionSummary(
  sessionId: string,
): Promise<TeacherSessionSummary> {
  return apiFetch<TeacherSessionSummary>(`/api/v1/sessions/${sessionId}/summary`);
}

export async function generateReadinessQuiz(payload: {
  sessionId: string;
  phase: QuizPhase;
}): Promise<GeneratedReadinessQuiz> {
  const user = getStoredAuthUser();
  if (user?.role !== "student") {
    throw new Error("Please log in as a student before taking the quiz.");
  }

  return apiFetch<GeneratedReadinessQuiz>("/api/v1/quiz/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitReadinessQuiz(payload: {
  quizId: string;
  answers: Array<{ questionId: string; answer: string }>;
}): Promise<SubmittedQuizResult> {
  const user = getStoredAuthUser();
  if (user?.role !== "student") {
    throw new Error("Please log in as a student before submitting the quiz.");
  }

  return apiFetch<SubmittedQuizResult>("/api/v1/quiz/submit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
