import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/sessions/[sessionId]/criteria
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } = await params

    // Check session exists
    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: { teacherId: true }
        }
      }
    })

    if (!session) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    // Check teacher owns this session
    if (session.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    const criteria = await prisma.sessionCriteria.findMany({
      where: { sessionId },
      include: {
        semesterCriteria: {
          select: {
            id: true,
            description: true,
            goal: true
          }
        }
      },
      orderBy: { order: "asc" }
    })

    return NextResponse.json({ criteria }, { status: 200 })

  } catch (error) {
    console.error("Get session criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// POST /api/v1/sessions/[sessionId]/criteria
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } =  await params
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
    }

    const { description, goal, order, semesterCriteriaId } = body

    // Validate required fields
    if (
      typeof description !== "string" || !description.trim() ||
      typeof goal !== "string" || !goal.trim() ||
      !Number.isInteger(order) || order < 0 ||
      (semesterCriteriaId !== undefined && semesterCriteriaId !== null && typeof semesterCriteriaId !== "string")
    ) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      )
    }

    // Check session exists
    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: { teacherId: true }
        }
      }
    })

    if (!session) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    // Check teacher owns this session
    if (session.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    if (semesterCriteriaId) {
      const semesterCriteria = await prisma.semesterCriteria.findFirst({
        where: { id: semesterCriteriaId, subjectId: session.subjectId },
        select: { id: true }
      })

      if (!semesterCriteria) {
        return NextResponse.json(
          { error: "Semester criteria not found for this session's subject" },
          { status: 404 }
        )
      }
    }

    const criteria = await prisma.sessionCriteria.create({
      data: {
        sessionId,
        description: description.trim(),
        goal: goal.trim(),
        order,
        semesterCriteriaId: semesterCriteriaId || null
      }
    })

    return NextResponse.json(
      { success: true, criteria },
      { status: 201 }
    )

  } catch (error) {
    console.error("Create session criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
