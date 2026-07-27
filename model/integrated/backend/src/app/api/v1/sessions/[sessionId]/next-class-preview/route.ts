import { NextRequest, NextResponse } from "next/server"
import { getPublishedPreviewForCurrentSession } from "@/lib/next-class-readiness"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  try {
    const studentId = request.headers.get("x-user-id")
    const { sessionId } = await params
    const preview = await getPublishedPreviewForCurrentSession(sessionId)

    if (!preview) {
      return NextResponse.json({ preview: null }, { status: 200 })
    }

    const answeredQuestionIds = new Set(
      preview.responses
        .filter((response) => response.studentId === studentId)
        .map((response) => response.questionId),
    )

    return NextResponse.json(
      {
        preview: {
          id: preview.id,
          currentSessionId: preview.currentSessionId,
          nextSessionId: preview.nextSessionId,
          title: preview.title,
          previewContent: preview.previewContent,
          status: preview.status,
          questions: preview.questions.map((question) => ({
            id: question.id,
            topic: question.topic,
            questionText: question.questionText,
            choices: question.choices,
            order: question.order,
            materialReferences: question.materialReferences,
            answered: answeredQuestionIds.has(question.id),
          })),
          submitted: preview.questions.length > 0 &&
            preview.questions.every((question) => answeredQuestionIds.has(question.id)),
        },
      },
      { status: 200 },
    )
  } catch (error) {
    console.error("Get student next-class preview error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
