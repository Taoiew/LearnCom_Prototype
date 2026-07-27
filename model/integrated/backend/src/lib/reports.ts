import { callAIInsight } from "@/lib/ai"
import { prisma } from "@/lib/prisma"

const getReadiness = (score: number) => score >= 80 ? "READY" : score >= 50 ? "PARTIAL" : "NOT_READY"

export const generateSessionReport = async (sessionId: string, teacherId: string) => {
  const session = await prisma.classSession.findUnique({
    where: { id: sessionId },
    include: {
      subject: { select: { teacherId: true } },
      sessionCriteria: { orderBy: { order: "asc" } },
      quizzes: {
        include: {
          student: { select: { id: true, name: true } },
          criteriaResults: { include: { criteria: { select: { id: true, description: true } } } },
          questions: { select: { score: true } }
        },
        orderBy: { takenAt: "desc" }
      },
      duringClassLogs: true
    }
  })

  if (!session) return { ok: false as const, error: "Session not found", status: 404 as const }
  if (session.subject.teacherId !== teacherId) return { ok: false as const, error: "Access denied", status: 403 as const }
  if (session.status !== "COMPLETED") return { ok: false as const, error: "Session is not completed yet", status: 400 as const }

  const submittedQuizzes = session.quizzes.filter((quiz) => quiz.questions.some((question) => question.score !== null))
  const latestQuizByStudent = new Map<string, typeof submittedQuizzes[number]>()
  for (const quiz of submittedQuizzes) {
    if (!latestQuizByStudent.has(quiz.studentId)) latestQuizByStudent.set(quiz.studentId, quiz)
  }
  const latestQuizzes = [...latestQuizByStudent.values()]
  const students = new Set([...latestQuizzes.map((quiz) => quiz.studentId), ...session.duringClassLogs.map((log) => log.studentId)])
  const averageReadiness = latestQuizzes.length === 0
    ? 0
    : latestQuizzes.reduce((sum, quiz) => sum + quiz.totalScore, 0) / latestQuizzes.length

  const weakCriteria = session.sessionCriteria.map((criterion) => {
    const results = latestQuizzes.flatMap((quiz) => quiz.criteriaResults.filter((result) => result.criteriaId === criterion.id))
    const failRate = results.length === 0
      ? 0
      : results.filter((result) => result.status !== "MET").length / results.length
    return { criteriaId: criterion.id, description: criterion.description, failRate }
  }).filter((criterion) => criterion.failRate > 0)

  const askedTopicCounts = new Map<string, number>()
  for (const log of session.duringClassLogs) {
    if (log.criteriaId) askedTopicCounts.set(log.criteriaId, (askedTopicCounts.get(log.criteriaId) ?? 0) + 1)
  }
  const mostAskedTopics = [...askedTopicCounts.entries()]
    .map(([criteriaId, count]) => {
      const criterion = session.sessionCriteria.find((item) => item.id === criteriaId)
      return criterion ? { criteriaId, description: criterion.description, count } : null
    })
    .filter((topic): topic is { criteriaId: string; description: string; count: number } => topic !== null)
    .sort((a, b) => b.count - a.count)

  const studentRecords = await Promise.all([...students].map(async (studentId) => {
    const quiz = latestQuizByStudent.get(studentId)
    const studentLogs = session.duringClassLogs.filter((log) => log.studentId === studentId)
    const studentQuizzes = await prisma.quiz.findMany({
      where: { studentId, session: { subjectId: session.subjectId } },
      include: { questions: { select: { score: true } } },
      orderBy: { takenAt: "desc" }
    })
    const latestBySession = new Map<string, typeof studentQuizzes[number]>()
    for (const studentQuiz of studentQuizzes) {
      if (studentQuiz.questions.some((question) => question.score !== null) && !latestBySession.has(studentQuiz.sessionId)) {
        latestBySession.set(studentQuiz.sessionId, studentQuiz)
      }
    }
    const allLatestScores = [...latestBySession.values()]
    const semesterProgressPercent = allLatestScores.length === 0
      ? 0
      : allLatestScores.reduce((sum, studentQuiz) => sum + studentQuiz.totalScore, 0) / allLatestScores.length
    const weakCriteriaIds = quiz?.criteriaResults.filter((result) => result.status !== "MET").map((result) => result.criteriaId) ?? []
    return {
      studentId,
      readinessScore: quiz?.totalScore ?? 0,
      weakCriteria: weakCriteriaIds,
      duringClassQCount: studentLogs.length,
      caughtUp: studentLogs.length > 0 && (quiz?.totalScore ?? 0) >= 50,
      semesterProgressPercent
    }
  }))

  const caughtUpCount = studentRecords.filter((student) => student.caughtUp).length
  const aiResult = await callAIInsight({
    criteriaResults: latestQuizzes.flatMap((quiz) => quiz.criteriaResults),
    duringClassLogs: session.duringClassLogs,
    caughtUpCount,
    totalStudents: students.size
  })

  const report = await prisma.sessionReport.upsert({
    where: { sessionId },
    create: {
      sessionId,
      avgReadiness: averageReadiness,
      weakCriteria,
      mostAskedTopics,
      aiInsight: aiResult.insight,
      studentCount: students.size,
      studentReports: {
        create: studentRecords.map((student) => ({
          student: { connect: { id: student.studentId } },
          readinessScore: student.readinessScore,
          weakCriteria: student.weakCriteria,
          duringClassQCount: student.duringClassQCount,
          caughtUp: student.caughtUp,
          semesterProgressPercent: student.semesterProgressPercent
        }))
      }
    },
    update: {
      avgReadiness: averageReadiness,
      weakCriteria,
      mostAskedTopics,
      aiInsight: aiResult.insight,
      studentCount: students.size,
      studentReports: {
        deleteMany: {},
        create: studentRecords.map((student) => ({
          student: { connect: { id: student.studentId } },
          readinessScore: student.readinessScore,
          weakCriteria: student.weakCriteria,
          duringClassQCount: student.duringClassQCount,
          caughtUp: student.caughtUp,
          semesterProgressPercent: student.semesterProgressPercent
        }))
      }
    }
  })

  return { ok: true as const, report, students: studentRecords.map((student) => ({ ...student, readiness: getReadiness(student.readinessScore) })) }
}
