import { NextRequest, NextResponse } from "next/server"
import { type CriteriaStatus, type Readiness } from "@prisma/client"
import { prisma } from "@/lib/prisma"
import { scoreQuizAnswer } from "@/lib/quiz"

type SubmittedAnswer = { questionId: string; answer: string }

const getReadiness = (totalScore: number): Readiness =>
  totalScore >= 80 ? "READY" : totalScore >= 50 ? "PARTIAL" : "NOT_READY"

const getCriteriaStatus = (averageScore: number): CriteriaStatus =>
  averageScore >= 80 ? "MET" : averageScore >= 50 ? "PARTIAL" : "NOT_MET"

export async function POST(request: NextRequest) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const language = request.headers.get("x-user-language") ?? "en"
    const body = await request.json()
    const { quizId, answers } = body ?? {}

    if (
      typeof quizId !== "string" ||
      !Array.isArray(answers) ||
      answers.length === 0 ||
      !answers.every((item): item is SubmittedAnswer =>
        item && typeof item.questionId === "string" && typeof item.answer === "string" && item.answer.trim())
    ) {
      return NextResponse.json({ error: "Missing or invalid answers" }, { status: 400 })
    }

    const quiz = await prisma.quiz.findFirst({
      where: { id: quizId, studentId },
      include: {
        questions: {
          include: { criteria: { select: { id: true, description: true } } },
          orderBy: { order: "asc" }
        }
      }
    })

    if (!quiz) {
      return NextResponse.json({ error: "Quiz not found" }, { status: 404 })
    }

    if (quiz.questions.some((question) => question.score !== null)) {
      return NextResponse.json({ error: "Quiz has already been submitted" }, { status: 409 })
    }

    const answerMap = new Map(answers.map((answer) => [answer.questionId, answer.answer.trim()]))
    if (answerMap.size !== quiz.questions.length || quiz.questions.some((question) => !answerMap.has(question.id))) {
      return NextResponse.json({ error: "An answer is required for every question" }, { status: 400 })
    }

    const scoredQuestions = await Promise.all(quiz.questions.map(async (question) => {
      const studentAnswer = answerMap.get(question.id)!
      const scored = await scoreQuizAnswer({
        questionText: question.questionText,
        correctConcept: question.correctConcept,
        studentAnswer,
        language,
        phase: quiz.phase === "AFTER" ? "AFTER" : "BEFORE"
      })
      return { question, studentAnswer, ...scored }
    }))

    const totalScore = scoredQuestions.reduce((sum, question) => sum + question.score, 0) / scoredQuestions.length
    const readiness = getReadiness(totalScore)
    const criteriaScores = new Map<string, typeof scoredQuestions>()

    for (const scoredQuestion of scoredQuestions) {
      const current = criteriaScores.get(scoredQuestion.question.criteriaId) ?? []
      current.push(scoredQuestion)
      criteriaScores.set(scoredQuestion.question.criteriaId, current)
    }

    const criteriaResults = [...criteriaScores.entries()].map(([criteriaId, questions]) => {
      const averageScore = questions.reduce((sum, question) => sum + question.score, 0) / questions.length
      return {
        criteriaId,
        description: questions[0].question.criteria.description,
        status: getCriteriaStatus(averageScore),
        feedback: questions.map((question) => question.feedback).join(" "),
        evidence: questions.map((question) => question.evidence).join("\n")
      }
    })

    await prisma.$transaction([
      ...scoredQuestions.map(({ question, studentAnswer, score, feedback }) =>
        prisma.quizQuestion.update({
          where: { id: question.id },
          data: { studentAnswer, score, feedback }
        })
      ),
      prisma.quiz.update({
        where: { id: quiz.id },
        data: {
          totalScore,
          readiness,
          criteriaResults: {
            create: criteriaResults.map(({ criteriaId, status, evidence }) => ({
              criteria: { connect: { id: criteriaId } },
              status,
              evidence
            }))
          }
        }
      })
    ])

    const weakCriteria = criteriaResults.filter((result) => result.status !== "MET").map((result) => result.criteriaId)
    return NextResponse.json(
      {
        quizId: quiz.id,
        totalScore,
        readiness,
        criteriaResults: criteriaResults.map(({ criteriaId, description, status, feedback }) => ({
          criteriaId,
          description,
          status,
          feedback
        })),
        weakCriteria,
        recommendation: weakCriteria.length > 0
          ? "Review the partially met criteria before continuing."
          : "You are ready to continue."
      },
      { status: 200 }
    )
  } catch (error) {
    console.error("Submit quiz error:", error)
    return NextResponse.json(
      {
        error: error instanceof Error
          ? `Quiz scoring failed: ${error.message}`
          : "Quiz scoring failed"
      },
      { status: 500 }
    )
  }
}
