import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

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
      select: {
        id: true,
        phase: true,
        totalScore: true,
        readiness: true,
        takenAt: true,
        criteriaResults: {
          select: {
            id: true,
            criteriaId: true,
            status: true,
            evidence: true,
            criteria: { select: { description: true, goal: true } }
          }
        }
      },
      orderBy: { takenAt: "desc" }
    })

    return NextResponse.json(
      {
        quizzes: quizzes.map((quiz) => ({
          ...quiz,
          quizId: quiz.id,
          id: undefined,
          criteriaResults: quiz.criteriaResults.map((result) => ({
            id: result.id,
            criteriaId: result.criteriaId,
            description: result.criteria.description,
            goal: result.criteria.goal,
            status: result.status,
            evidence: result.evidence
          }))
        }))
      },
      { status: 200 }
    )
  } catch (error) {
    console.error("Get quiz history error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
