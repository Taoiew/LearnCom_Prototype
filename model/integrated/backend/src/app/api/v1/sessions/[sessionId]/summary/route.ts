import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

type AttendanceRow = {
  id: string
  studentId: string
  studentName: string
  photoUrl: string
  checkedInAt: Date
}

type MaterialRef = {
  materialId: string
  fileName: string
  pageNumber: number | null
}

type AnswerRef = {
  id: string
  messageId: string
  studentMessageId: string | null
  sourceType: "MATERIAL" | "EXTERNAL_AI"
  sourceName: string | null
  materialId: string | null
  materialFileName: string | null
  pageNumber: number | null
  sourceQuote: string | null
  provider: string | null
  createdAt: Date
}

type SummaryQuestion = {
  id: string
  studentId: string
  studentName: string
  content: string
  createdAt: Date
  imageUrl: string | null
  materialRefs: MaterialRef[]
  answerReferences: AnswerRef[]
}

const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "can",
  "could",
  "did",
  "for",
  "has",
  "have",
  "into",
  "is",
  "it",
  "its",
  "me",
  "of",
  "on",
  "or",
  "please",
  "show",
  "tell",
  "the",
  "there",
  "to",
  "will",
  "what",
  "when",
  "where",
  "why",
  "who",
  "this",
  "that",
  "about",
  "session",
  "course",
  "slide",
  "convey",
  "page",
  "does",
  "mean",
  "explain",
  "using",
  "from",
  "with",
  "many",
  "much",
  "more",
  "less",
  "difference",
  "different",
])

const COURSE_TOPIC_PHRASES = [
  "amazon web services",
  "aws cloud adoption framework",
  "cloud adoption framework",
  "cloud computing",
  "cloud concepts",
  "aws services",
  "aws service categories",
  "compute services",
  "storage and database",
  "security identity and compliance",
  "security groups",
  "network acls",
  "network acl",
  "traditional it",
  "on premises",
  "amazon ec2",
  "ec2 instances",
  "aws lambda",
  "elastic beanstalk",
  "auto scaling",
  "amazon ecs",
  "amazon eks",
  "amazon ecr",
  "aws fargate",
  "aws iam",
  "iam roles",
  "amazon cognito",
  "amazon vpc",
  "elastic load balancing",
  "amazon rds",
  "amazon s3",
  "amazon efs",
  "storage services",
  "networking services",
  "security services",
]

const DOMAIN_TERMS = new Set([
  "aws",
  "ec2",
  "iam",
  "lambda",
  "vpc",
  "rds",
  "s3",
  "efs",
  "ecs",
  "eks",
  "ecr",
  "fargate",
  "cognito",
  "cloud",
  "compute",
  "storage",
  "database",
  "networking",
  "security",
  "identity",
  "compliance",
  "scaling",
  "serverless",
])

function tokenizeTopicText(value: string) {
  return value
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, " ")
    .split(/\s+/)
    .filter((word) => word.length > 2 && !STOP_WORDS.has(word))
}

function prettifyTopic(topic: string) {
  return topic
    .replace(/\baws\b/g, "AWS")
    .replace(/\bec2\b/g, "EC2")
    .replace(/\biam\b/g, "IAM")
    .replace(/\bvpc\b/g, "VPC")
    .replace(/\brds\b/g, "RDS")
    .replace(/\bs3\b/g, "S3")
    .replace(/\befs\b/g, "EFS")
    .replace(/\becs\b/g, "ECS")
    .replace(/\beks\b/g, "EKS")
    .replace(/\becr\b/g, "ECR")
}

function extractCourseTopics(question: SummaryQuestion) {
  const referenceText = question.answerReferences
    .map((reference) => [
      reference.sourceQuote,
      reference.sourceName,
      reference.materialFileName,
      reference.materialId,
    ].filter(Boolean).join(" "))
    .join(" ")
  const combinedText = `${question.content} ${referenceText}`.toLowerCase()
  const candidates = new Set<string>()

  for (const phrase of COURSE_TOPIC_PHRASES) {
    if (combinedText.includes(phrase)) {
      candidates.add(phrase)
    }
  }

  const words = tokenizeTopicText(combinedText)
  if (words.includes("service") || words.includes("services")) {
    candidates.add("aws services")
  }

  for (const word of words) {
    if (DOMAIN_TERMS.has(word)) {
      candidates.add(word)
    }
  }

  for (let index = 0; index < words.length - 1; index += 1) {
    const first = words[index]
    const second = words[index + 1]
    if (DOMAIN_TERMS.has(first) || DOMAIN_TERMS.has(second)) {
      candidates.add(`${first} ${second}`)
    }
  }

  return [...candidates].slice(0, 8)
}

function extractTopicRanking(questions: SummaryQuestion[]) {
  const topics = new Map<
    string,
    {
      topic: string
      count: number
      questionIds: Set<string>
      materialRefs: Map<string, MaterialRef>
    }
  >()

  for (const question of questions) {
    const questionTopics = extractCourseTopics(question)

    for (const questionTopic of questionTopics) {
      const topic = topics.get(questionTopic) ?? {
        topic: questionTopic,
        count: 0,
        questionIds: new Set<string>(),
        materialRefs: new Map<string, MaterialRef>(),
      }

      topic.count += 1
      topic.questionIds.add(question.id)

      for (const materialRef of question.materialRefs) {
        const key = `${materialRef.materialId}:${materialRef.pageNumber ?? ""}`
        topic.materialRefs.set(key, materialRef)
      }

      for (const answerRef of question.answerReferences) {
        if (answerRef.sourceType !== "MATERIAL") continue
        const materialId = answerRef.materialId ?? "material"
        const fileName = answerRef.materialFileName ?? answerRef.sourceName ?? materialId
        const key = `${materialId}:${answerRef.pageNumber ?? ""}`
        topic.materialRefs.set(key, {
          materialId,
          fileName,
          pageNumber: answerRef.pageNumber,
        })
      }

      topics.set(questionTopic, topic)
    }
  }

  return [...topics.values()]
    .sort((a, b) => b.count - a.count || a.topic.localeCompare(b.topic))
    .slice(0, 8)
    .map((topic) => ({
      topic: prettifyTopic(topic.topic),
      count: topic.count,
      questionCount: topic.questionIds.size,
      materialRefs: [...topic.materialRefs.values()],
    }))
}

function summarizeQuizzes(quizzes: Array<{
  id: string
  phase: "BEFORE" | "DURING" | "AFTER"
  totalScore: number
  readiness: "READY" | "PARTIAL" | "NOT_READY"
  takenAt: Date
  student: { id: string; name: string }
  questions: Array<{ score: number | null; studentAnswer: string | null }>
  criteriaResults: Array<{
    criteriaId: string
    status: "MET" | "PARTIAL" | "NOT_MET"
    criteria: { description: string }
  }>
}>) {
  const submittedQuizzes = quizzes.filter((quiz) =>
    quiz.questions.some((question) => question.score !== null)
  )
  const averageScore = submittedQuizzes.length === 0
    ? 0
    : submittedQuizzes.reduce((sum, quiz) => sum + quiz.totalScore, 0) / submittedQuizzes.length

  const latestSubmittedByStudentAndPhase = new Map<string, typeof submittedQuizzes[number]>()
  for (const quiz of submittedQuizzes) {
    const key = `${quiz.student.id}:${quiz.phase}`
    const current = latestSubmittedByStudentAndPhase.get(key)
    if (!current || quiz.takenAt > current.takenAt) {
      latestSubmittedByStudentAndPhase.set(key, quiz)
    }
  }

  const phaseSummaries = (["BEFORE", "AFTER"] as const).map((phase) => {
    const phaseQuizzes = quizzes.filter((quiz) => quiz.phase === phase)
    const phaseSubmitted = submittedQuizzes.filter((quiz) => quiz.phase === phase)
    const latestSubmitted = [...latestSubmittedByStudentAndPhase.values()]
      .filter((quiz) => quiz.phase === phase)
    const phaseAverage = phaseSubmitted.length === 0
      ? 0
      : phaseSubmitted.reduce((sum, quiz) => sum + quiz.totalScore, 0) / phaseSubmitted.length

    return {
      phase,
      attempts: phaseQuizzes.length,
      submittedAttempts: phaseSubmitted.length,
      studentsSubmitted: new Set(phaseSubmitted.map((quiz) => quiz.student.id)).size,
      averageScore: Math.round(phaseAverage),
      readyCount: latestSubmitted.filter((quiz) => quiz.readiness === "READY").length,
      partialCount: latestSubmitted.filter((quiz) => quiz.readiness === "PARTIAL").length,
      notReadyCount: latestSubmitted.filter((quiz) => quiz.readiness === "NOT_READY").length,
    }
  })

  const criteriaMap = new Map<string, {
    criteriaId: string
    description: string
    metCount: number
    partialCount: number
    notMetCount: number
  }>()

  for (const quiz of submittedQuizzes) {
    for (const result of quiz.criteriaResults) {
      const current = criteriaMap.get(result.criteriaId) ?? {
        criteriaId: result.criteriaId,
        description: result.criteria.description,
        metCount: 0,
        partialCount: 0,
        notMetCount: 0,
      }

      if (result.status === "MET") current.metCount += 1
      if (result.status === "PARTIAL") current.partialCount += 1
      if (result.status === "NOT_MET") current.notMetCount += 1
      criteriaMap.set(result.criteriaId, current)
    }
  }

  return {
    totalAttempts: quizzes.length,
    submittedAttempts: submittedQuizzes.length,
    averageScore: Math.round(averageScore),
    studentsSubmitted: new Set(submittedQuizzes.map((quiz) => quiz.student.id)).size,
    studentsPassed: [...latestSubmittedByStudentAndPhase.values()]
      .filter((quiz) => quiz.phase === "AFTER" && quiz.readiness === "READY")
      .length,
    phases: phaseSummaries,
    criteriaBreakdown: [...criteriaMap.values()]
      .sort((a, b) =>
        (b.notMetCount + b.partialCount) - (a.notMetCount + a.partialCount) ||
        a.description.localeCompare(b.description)
      )
      .slice(0, 6),
    recentAttempts: quizzes.slice(0, 8).map((quiz) => ({
      quizId: quiz.id,
      studentId: quiz.student.id,
      studentName: quiz.student.name,
      phase: quiz.phase,
      submitted: quiz.questions.some((question) => question.score !== null),
      totalScore: Math.round(quiz.totalScore),
      readiness: quiz.readiness,
      questionCount: quiz.questions.length,
      takenAt: quiz.takenAt,
    })),
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } = await params

    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: {
            id: true,
            name: true,
            teacherId: true,
          },
        },
      },
    })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    if (session.subject.teacherId !== teacherId) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const [messages, chatImages, attendanceRows, answerReferences, quizzes, nextClassPreviews] = await Promise.all([
      prisma.message.findMany({
        where: {
          role: "STUDENT",
          conversation: { sessionId },
        },
        include: {
          student: { select: { id: true, name: true } },
        },
        orderBy: { createdAt: "desc" },
      }),
      prisma.chatImageLog.findMany({
        where: { sessionId },
        include: {
          student: { select: { id: true, name: true } },
          material: { select: { id: true, fileName: true } },
        },
        orderBy: { createdAt: "desc" },
      }),
      prisma.$queryRaw<AttendanceRow[]>`
        SELECT
          a.id,
          a."studentId",
          u.name AS "studentName",
          a."photoUrl",
          a."checkedInAt"
        FROM "Attendance" a
        JOIN "User" u ON u.id = a."studentId"
        WHERE a."sessionId" = ${sessionId}
        ORDER BY a."checkedInAt" DESC
      `,
      prisma.answerReference.findMany({
        where: { sessionId },
        orderBy: { createdAt: "asc" },
      }),
      prisma.quiz.findMany({
        where: { sessionId },
        include: {
          student: { select: { id: true, name: true } },
          questions: { select: { score: true, studentAnswer: true } },
          criteriaResults: {
            include: {
              criteria: { select: { description: true } },
            },
          },
        },
        orderBy: { takenAt: "desc" },
      }),
      prisma.nextClassPreview.findMany({
        where: { currentSessionId: sessionId },
        include: {
          questions: { orderBy: { order: "asc" } },
          summary: { include: { revisionNotes: { orderBy: { createdAt: "desc" } } } },
        },
        orderBy: { createdAt: "desc" },
      }),
    ])

    const imagesByMessageId = new Map<string, typeof chatImages>()
    for (const image of chatImages) {
      imagesByMessageId.set(image.messageId, [
        ...(imagesByMessageId.get(image.messageId) ?? []),
        image,
      ])
    }

    const messageById = new Map(messages.map((message) => [message.id, message]))
    const answerReferencesByStudentMessageId = new Map<string, AnswerRef[]>()

    for (const reference of answerReferences) {
      if (!reference.studentMessageId) continue
      answerReferencesByStudentMessageId.set(reference.studentMessageId, [
        ...(answerReferencesByStudentMessageId.get(reference.studentMessageId) ?? []),
        {
          id: reference.id,
          messageId: reference.messageId,
          studentMessageId: reference.studentMessageId,
          sourceType: reference.sourceType,
          sourceName: reference.sourceName,
          materialId: reference.materialId,
          materialFileName: reference.materialFileName,
          pageNumber: reference.pageNumber,
          sourceQuote: reference.sourceQuote,
          provider: reference.provider,
          createdAt: reference.createdAt,
        },
      ])
    }

    const questions: SummaryQuestion[] = messages.map((message) => {
      const matchingImages = imagesByMessageId.get(message.id) ?? []

      return {
        id: message.id,
        studentId: message.studentId,
        studentName: message.student.name,
        content: message.content,
        createdAt: message.createdAt,
        imageUrl: matchingImages[0]?.imageUrl ?? null,
        answerReferences: answerReferencesByStudentMessageId.get(message.id) ?? [],
        materialRefs: matchingImages
          .filter((image) => image.material)
          .map((image) => ({
            materialId: image.material!.id,
            fileName: image.material!.fileName,
            pageNumber: image.pageNumber,
          })),
      }
    })

    const topicRanking = extractTopicRanking(questions)

    const attendances = attendanceRows.map((attendance) => ({
      id: attendance.id,
      studentId: attendance.studentId,
      studentName: attendance.studentName,
      photoUrl: attendance.photoUrl,
      checkedInAt: attendance.checkedInAt,
    }))

    return NextResponse.json(
      {
        session: {
          id: session.id,
          title: session.title,
          status: session.status,
          phase: session.phase,
          date: session.date,
          durationMinutes: session.durationMinutes,
          subject: {
            id: session.subject.id,
            name: session.subject.name,
          },
        },
        stats: {
          studentsAttended: attendances.length,
          questionsAsked: questions.length,
          chatImagesSent: chatImages.length,
          attendancePhotos: attendances.filter((attendance) => attendance.photoUrl).length,
          topTopic: topicRanking[0]?.topic ?? "No topic yet",
        },
        topicRanking,
        quizOverview: summarizeQuizzes(quizzes),
        nextClassReadiness: nextClassPreviews.map((preview) => ({
          id: preview.id,
          currentSessionId: preview.currentSessionId,
          nextSessionId: preview.nextSessionId,
          title: preview.title,
          previewContent: preview.previewContent,
          status: preview.status,
          createdAt: preview.createdAt,
          publishedAt: preview.publishedAt,
          questions: preview.questions,
          summary: preview.summary,
        })),
        questions,
        answerReferences: answerReferences.map((reference) => {
          const studentQuestion = reference.studentMessageId
            ? messageById.get(reference.studentMessageId)
            : undefined

          return {
            id: reference.id,
            messageId: reference.messageId,
            studentMessageId: reference.studentMessageId,
            studentId: reference.studentId,
            studentName: studentQuestion?.student.name ?? "Student",
            question: studentQuestion?.content ?? "",
            sourceType: reference.sourceType,
            sourceName: reference.sourceName,
            materialId: reference.materialId,
            materialFileName: reference.materialFileName,
            pageNumber: reference.pageNumber,
            sourceQuote: reference.sourceQuote,
            provider: reference.provider,
            createdAt: reference.createdAt,
          }
        }),
        attendances,
        chatImages: chatImages.map((image) => ({
          id: image.id,
          studentId: image.studentId,
          studentName: image.student.name,
          imageUrl: image.imageUrl,
          materialId: image.materialId,
          materialFileName: image.material?.fileName ?? null,
          pageNumber: image.pageNumber,
          messageId: image.messageId,
          messageContent: messageById.get(image.messageId)?.content ?? "",
          createdAt: image.createdAt,
        })),
      },
      { status: 200 },
    )
  } catch (error) {
    console.error("Get session summary error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    )
  }
}
