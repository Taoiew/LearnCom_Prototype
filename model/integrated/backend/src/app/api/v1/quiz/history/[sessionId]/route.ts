import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/quiz/history/[sessionId] — list a student's quiz attempts for a session
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const { sessionId } = await params
    const session = await prisma.classSession.findUnique({ where: { id: sessionId }, select: { id: true } })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    const quizzes = await prisma.quiz.findMany({
      where: { studentId, sessionId },
      select: { id: true, phase: true, totalScore: true, readiness: true, takenAt: true },
      orderBy: { takenAt: "desc" }
    })

    return NextResponse.json(
      { quizzes: quizzes.map((quiz) => ({ ...quiz, quizId: quiz.id, id: undefined })) },
      { status: 200 }
    )
  } catch (error) {
    console.error("Get quiz history error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
