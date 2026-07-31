import { NextRequest, NextResponse } from "next/server"
import { ensureActiveSession } from "@/lib/chat"
import { prisma } from "@/lib/prisma"
import { generateQuizFromKbAndRubric, type PersonalizationContext, type QuizPhase } from "@/lib/quiz"

const MAX_QUIZZES_PER_PHASE = 3

type QuizQuestionResponse = {
  id: string
  criteriaId: string
  order: number
  questionText: string
  questionType: string
  options: unknown
  criteria: {
    description: string
    goal: string
  }
}

const buildPostQuizPersonalization = async ({
  studentId,
  sessionId
}: {
  studentId: string
  sessionId: string
}): Promise<PersonalizationContext> => {
  const [previousPreQuizzes, recentMessages] = await Promise.all([
    prisma.quiz.findMany({
      where: {
        studentId,
        sessionId,
        phase: "BEFORE"
      },
      include: {
        criteriaResults: {
          include: {
            criteria: { select: { id: true, description: true } }
          }
        },
        questions: {
          select: {
            feedback: true,
            criteriaId: true,
            questionText: true,
            studentAnswer: true
          }
        }
      },
      orderBy: { takenAt: "desc" },
      take: 2
    }),
    prisma.message.findMany({
      where: {
        studentId,
        role: "STUDENT",
        conversation: { sessionId }
      },
      select: { content: true },
      orderBy: { createdAt: "desc" },
      take: 8
    })
  ])

  const weakCriteriaIds = new Set<string>()
  const previousFeedback: string[] = []

  for (const quiz of previousPreQuizzes) {
    for (const result of quiz.criteriaResults) {
      if (result.status !== "MET") {
        weakCriteriaIds.add(result.criteriaId)
        previousFeedback.push(`${result.criteria.description}: ${result.evidence}`)
      }
    }

    for (const question of quiz.questions) {
      if (question.feedback) {
        previousFeedback.push(question.feedback)
      }
    }
  }

  return {
    weakCriteriaIds: [...weakCriteriaIds],
    recentStudentQuestions: recentMessages.map((message) => message.content),
    previousFeedback
  }
}

export async function POST(request: NextRequest) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const language = request.headers.get("x-user-language") ?? "en"
    const body = await request.json()
    const { sessionId, phase } = body ?? {}

    if (typeof sessionId !== "string" || !["BEFORE", "AFTER"].includes(phase)) {
      return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 })
    }
    const quizPhase = phase as QuizPhase

    const sessionResult = await ensureActiveSession(sessionId)
    if (!sessionResult.ok) {
      return NextResponse.json({ error: sessionResult.error }, { status: sessionResult.status })
    }

    if (sessionResult.session.sessionCriteria.length === 0) {
      const defaultCriterion = await prisma.sessionCriteria.create({
        data: {
          sessionId,
          description: `Explain the main concept from ${sessionResult.session.title} using specific evidence from the uploaded materials`,
          goal: sessionResult.session.materials.length
            ? `Identify the session's main idea, cite concrete material evidence from ${sessionResult.session.materials.map((material) => material.fileName).join(", ")}, and apply it to a realistic example.`
            : `Show readiness for ${sessionResult.session.title} by explaining the main concept and giving a realistic example.`,
          order: 0
        }
      })
      sessionResult.session.sessionCriteria.push(defaultCriterion)
    }

    const quizCount = await prisma.quiz.count({
      where: { studentId, sessionId, phase: quizPhase }
    })
    if (quizCount >= MAX_QUIZZES_PER_PHASE) {
      return NextResponse.json({ error: "Quiz attempt limit reached" }, { status: 429 })
    }

    const personalization = quizPhase === "AFTER"
      ? await buildPostQuizPersonalization({ studentId, sessionId })
      : undefined

    const generatedQuestions = await generateQuizFromKbAndRubric({
      session: sessionResult.session,
      studentId,
      language,
      phase: quizPhase,
      personalization
    })

    const quiz = await prisma.quiz.create({
      data: {
        studentId,
        sessionId,
        phase: quizPhase,
        questions: {
          create: generatedQuestions.map((question) => ({
            criteria: { connect: { id: question.criteriaId } },
            questionText: question.questionText,
            questionType: question.questionType,
            ...(question.options !== null && { options: question.options }),
            correctConcept: question.correctConcept,
            order: question.order
          }))
        }
      },
      include: {
        questions: {
          include: {
            criteria: {
              select: { description: true, goal: true }
            }
          },
          orderBy: { order: "asc" }
        }
      }
    })
    const sourceExcerptByCriteriaId = new Map(
      generatedQuestions.map((question) => [question.criteriaId, question.sourceExcerpt])
    )

    return NextResponse.json(
      {
        quizId: quiz.id,
        phase: quiz.phase,
        questions: (quiz.questions as QuizQuestionResponse[])
          .map(({ id, criteriaId, order, questionText, questionType, options, criteria }) => ({
          id,
          criteriaId,
          order,
          questionText,
          questionType,
          options,
          rubric: {
            description: criteria.description,
            goal: criteria.goal
          },
          sourceExcerpt: sourceExcerptByCriteriaId.get(criteriaId) ?? ""
        }))
      },
      { status: 200 }
    )
  } catch (error) {
    console.error("Generate quiz error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
