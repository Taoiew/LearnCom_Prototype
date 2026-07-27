import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// POST /api/v1/training/store — trusted service endpoint for external-AI answers
export async function POST(request: NextRequest) {
  try {
    const internalSecret = process.env.INTERNAL_API_SECRET
    if (!internalSecret || request.headers.get("x-internal-api-secret") !== internalSecret) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const body = await request.json()
    const { question, answer, source, sessionId, studentId, topic } = body ?? {}

    if (
      typeof question !== "string" || !question.trim() ||
      typeof answer !== "string" || !answer.trim() ||
      typeof source !== "string" || !source.trim() ||
      typeof sessionId !== "string" ||
      typeof studentId !== "string" ||
      (topic !== undefined && topic !== null && typeof topic !== "string")
    ) {
      return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 })
    }

    const [session, student] = await Promise.all([
      prisma.classSession.findUnique({ where: { id: sessionId }, select: { id: true } }),
      prisma.user.findUnique({ where: { id: studentId }, select: { id: true, role: true } })
    ])
    if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 })
    if (!student || student.role !== "STUDENT") {
      return NextResponse.json({ error: "Student not found" }, { status: 404 })
    }

    const trainingData = await prisma.trainingData.create({
      data: {
        question: question.trim(),
        answer: answer.trim(),
        source: source.trim(),
        sessionId,
        studentId,
        topic: topic?.trim() || null
      }
    })

    return NextResponse.json({ success: true, id: trainingData.id }, { status: 201 })
  } catch (error) {
    console.error("Store training data error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
