import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"
import { analyzePreview } from "@/lib/next-class-readiness"

type SubmittedAnswer = {
  questionId: string
  selectedChoiceIndex: number
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ previewId: string }> },
) {
  try {
    const studentId = request.headers.get("x-user-id")
    const userRole = request.headers.get("x-user-role")
    const { previewId } = await params
    const body = await request.json()
    const { answers } = body ?? {}

    if (
      userRole !== "STUDENT" ||
      typeof studentId !== "string" ||
      !Array.isArray(answers) ||
      answers.length === 0 ||
      !answers.every((answer): answer is SubmittedAnswer =>
        answer &&
        typeof answer.questionId === "string" &&
        Number.isInteger(answer.selectedChoiceIndex))
    ) {
      return NextResponse.json({ error: "Missing or invalid answers" }, { status: 400 })
    }

    const preview = await prisma.nextClassPreview.findUnique({
      where: { id: previewId },
      include: { questions: true },
    })

    if (!preview || preview.status !== "PUBLISHED") {
      return NextResponse.json({ error: "Preview not found" }, { status: 404 })
    }

    const answerMap = new Map(answers.map((answer) => [answer.questionId, answer.selectedChoiceIndex]))
    if (
      preview.questions.length === 0 ||
      answerMap.size !== preview.questions.length ||
      preview.questions.some((question) => !answerMap.has(question.id))
    ) {
      return NextResponse.json({ error: "Answer every question before submitting" }, { status: 400 })
    }

    const responseWrites = preview.questions.map((question) => {
      const selectedChoiceIndex = answerMap.get(question.id)!
      const choices = question.choices as string[]
      if (selectedChoiceIndex < 0 || selectedChoiceIndex >= choices.length) {
        throw new Error("Invalid choice selected")
      }

      return prisma.nextClassReadinessResponse.upsert({
        where: {
          questionId_studentId: {
            questionId: question.id,
            studentId,
          },
        },
        create: {
          previewId,
          questionId: question.id,
          studentId,
          selectedChoiceIndex,
          isCorrect: selectedChoiceIndex === question.correctChoiceIndex,
        },
        update: {
          selectedChoiceIndex,
          isCorrect: selectedChoiceIndex === question.correctChoiceIndex,
          answeredAt: new Date(),
        },
      })
    })

    const responses = await prisma.$transaction(responseWrites)
    const correctCount = responses.filter((response) => response.isCorrect).length
    const score = Math.round((correctCount / responses.length) * 100)
    const summary = await analyzePreview(previewId)

    return NextResponse.json(
      {
        previewId,
        score,
        correctCount,
        totalQuestions: responses.length,
        readiness:
          score >= 80 ? "READY" : score >= 60 ? "PARTIALLY_READY" : "NEEDS_REVIEW",
        summary,
      },
      { status: 200 },
    )
  } catch (error) {
    console.error("Submit next-class readiness error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 },
    )
  }
}
