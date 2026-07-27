import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/sessions/[sessionId] — get single session with full details
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const userId = request.headers.get("x-user-id")
    const userRole = request.headers.get("x-user-role")
    const { sessionId } = await params

    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: {
            id: true,
            name: true,
            teacherId: true
          }
        },
        sessionCriteria: {
          orderBy: { order: "asc" }
        },
        materials: {
          orderBy: { uploadedAt: "desc" }
        }
      }
    })

    if (!session) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    // Teacher can only see their own sessions
    if (userRole === "TEACHER" && session.subject.teacherId !== userId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    // Student can only see active sessions
    if (userRole === "STUDENT" && session.status !== "ACTIVE") {
      return NextResponse.json(
        { error: "Session is not active" },
        { status: 403 }
      )
    }

    return NextResponse.json({ session }, { status: 200 })

  } catch (error) {
    console.error("Get session error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// PATCH /api/v1/sessions/[sessionId] — update session details
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } = await params
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    const { title, description, date, durationMinutes } = body
    const sessionDate = date !== undefined ? new Date(date) : null
    const sessionDurationMinutes =
      durationMinutes === undefined ? undefined : Number(durationMinutes)

    if (
      (title !== undefined && (typeof title !== "string" || !title.trim())) ||
      (description !== undefined && description !== null && typeof description !== "string") ||
      (date !== undefined && (typeof date !== "string" || Number.isNaN(sessionDate!.getTime()))) ||
      (
        durationMinutes !== undefined &&
        (
          !Number.isInteger(sessionDurationMinutes) ||
          (sessionDurationMinutes ?? 0) < 5 ||
          (sessionDurationMinutes ?? 0) > 720
        )
      )
    ) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    // Check session exists
    const existing = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: { teacherId: true }
        }
      }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    // Check teacher owns this session
    if (existing.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    const session = await prisma.classSession.update({
      where: { id: sessionId },
      data: {
        title: title !== undefined ? title.trim() : existing.title,
        description: description !== undefined ? description?.trim() || null : existing.description,
        date: sessionDate || existing.date,
        durationMinutes: sessionDurationMinutes ?? existing.durationMinutes
      }
    })

    return NextResponse.json(
      { success: true, session },
      { status: 200 }
    )

  } catch (error) {
    console.error("Update session error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// DELETE /api/v1/sessions/[sessionId] — delete session
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } = await params

    // Check session exists
    const existing = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: { teacherId: true }
        }
      }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    // Check teacher owns this session
    if (existing.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    const [criteria, conversations, quizzes, report, previews] = await Promise.all([
      prisma.sessionCriteria.findMany({
        where: { sessionId },
        select: { id: true },
      }),
      prisma.conversation.findMany({
        where: { sessionId },
        select: { id: true },
      }),
      prisma.quiz.findMany({
        where: { sessionId },
        select: { id: true },
      }),
      prisma.sessionReport.findUnique({
        where: { sessionId },
        select: { id: true },
      }),
      prisma.nextClassPreview.findMany({
        where: {
          OR: [
            { currentSessionId: sessionId },
            { nextSessionId: sessionId },
          ],
        },
        select: { id: true },
      }),
    ])

    const criteriaIds = criteria.map((criterion) => criterion.id)
    const conversationIds = conversations.map((conversation) => conversation.id)
    const quizIds = quizzes.map((quiz) => quiz.id)
    const previewIds = previews.map((preview) => preview.id)

    await prisma.$transaction([
      prisma.teacherRevisionNote.deleteMany({
        where: {
          OR: [
            { nextSessionId: sessionId },
            { summary: { previewId: { in: previewIds } } },
          ],
        },
      }),
      prisma.nextClassFeedbackSummary.deleteMany({
        where: { previewId: { in: previewIds } },
      }),
      prisma.nextClassReadinessResponse.deleteMany({
        where: { previewId: { in: previewIds } },
      }),
      prisma.nextClassReadinessQuestion.deleteMany({
        where: { previewId: { in: previewIds } },
      }),
      prisma.nextClassPreview.deleteMany({
        where: { id: { in: previewIds } },
      }),
      prisma.answerReference.deleteMany({
        where: { sessionId },
      }),
      prisma.chatImageLog.deleteMany({
        where: { sessionId },
      }),
      prisma.attendance.deleteMany({
        where: { sessionId },
      }),
      prisma.trainingData.deleteMany({
        where: { sessionId },
      }),
      prisma.duringClassLog.deleteMany({
        where: { sessionId },
      }),
      prisma.criteriaResult.deleteMany({
        where: {
          OR: [
            { quizId: { in: quizIds } },
            { criteriaId: { in: criteriaIds } },
          ],
        },
      }),
      prisma.quizQuestion.deleteMany({
        where: {
          OR: [
            { quizId: { in: quizIds } },
            { criteriaId: { in: criteriaIds } },
          ],
        },
      }),
      prisma.quiz.deleteMany({
        where: { sessionId },
      }),
      prisma.conversationSummary.deleteMany({
        where: { conversationId: { in: conversationIds } },
      }),
      prisma.message.deleteMany({
        where: { conversationId: { in: conversationIds } },
      }),
      prisma.conversation.deleteMany({
        where: { sessionId },
      }),
      prisma.studentReport.deleteMany({
        where: report ? { sessionReportId: report.id } : { id: { in: [] } },
      }),
      prisma.sessionReport.deleteMany({
        where: { sessionId },
      }),
      prisma.material.deleteMany({
        where: { sessionId },
      }),
      prisma.sessionCriteria.deleteMany({
        where: { sessionId },
      }),
      prisma.classSession.delete({
        where: { id: sessionId },
      }),
    ])

    return NextResponse.json(
      { success: true },
      { status: 200 }
    )

  } catch (error) {
    console.error("Delete session error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
