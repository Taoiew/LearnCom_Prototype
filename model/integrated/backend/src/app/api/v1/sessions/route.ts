import { NextRequest, NextResponse } from "next/server"
import { randomUUID } from "crypto"
import { prisma } from "@/lib/prisma"

// GET /api/v1/sessions — students get active sessions, teachers get all their sessions
export async function GET(request: NextRequest) {
  try {
    const userId = request.headers.get("x-user-id")
    const userRole = request.headers.get("x-user-role")
    const subjectId = request.nextUrl.searchParams.get("subjectId")

    let sessions

    if (userRole === "TEACHER") {
      // Teacher gets all their sessions
      sessions = await prisma.classSession.findMany({
        where: {
          subject: { teacherId: userId! },
          ...(subjectId && { subjectId })
        },
        include: {
          subject: {
            select: { name: true }
          },
          _count: {
            select: {
              sessionCriteria: true,
              materials: true
            }
          }
        },
        orderBy: { date: "asc" }
      })
    } else {
      // Student gets active sessions only
      sessions = await prisma.classSession.findMany({
        where: {
          status: "ACTIVE",
          ...(subjectId && { subjectId })
        },
        include: {
          subject: {
            select: { name: true }
          },
          _count: {
            select: {
              sessionCriteria: true,
              materials: true
            }
          }
        },
        orderBy: { date: "asc" }
      })
    }

    return NextResponse.json({ sessions }, { status: 200 })

  } catch (error) {
    console.error("Get sessions error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// POST /api/v1/sessions — create a new class session
export async function POST(request: NextRequest) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
    }

    const { subjectId, title, description, date, durationMinutes } = body
    const sessionDate = new Date(date)
    const sessionDurationMinutes =
      durationMinutes === undefined ? 180 : Number(durationMinutes)

    // Validate required fields
    if (
      typeof subjectId !== "string" ||
      typeof title !== "string" ||
      !title.trim() ||
      typeof date !== "string" ||
      Number.isNaN(sessionDate.getTime()) ||
      !Number.isInteger(sessionDurationMinutes) ||
      sessionDurationMinutes < 5 ||
      sessionDurationMinutes > 720 ||
      (description !== undefined && description !== null && typeof description !== "string")
    ) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      )
    }

    // Check subject exists and teacher owns it
    const subject = await prisma.subject.findUnique({
      where: { id: subjectId }
    })

    if (!subject) {
      return NextResponse.json(
        { error: "Subject not found" },
        { status: 404 }
      )
    }

    if (subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    const sessionId = `session_${randomUUID()}`
    const sessions = await prisma.$queryRaw<Array<{
      id: string
      subjectId: string
      title: string
      description: string | null
      date: Date
      durationMinutes: number
      status: string
      phase: string
      createdAt: Date
    }>>`
      INSERT INTO "ClassSession" (
        "id",
        "subjectId",
        "title",
        "description",
        "date",
        "durationMinutes",
        "status",
        "phase",
        "createdAt"
      )
      VALUES (
        ${sessionId},
        ${subjectId},
        ${title.trim()},
        ${description?.trim() || null},
        ${sessionDate},
        ${sessionDurationMinutes},
        'UPCOMING'::"SessionStatus",
        'BEFORE'::"Phase",
        NOW()
      )
      RETURNING
        "id",
        "subjectId",
        "title",
        "description",
        "date",
        "durationMinutes",
        "status"::text AS "status",
        "phase"::text AS "phase",
        "createdAt"
    `
    const session = sessions[0]

    return NextResponse.json(
      { success: true, session },
      { status: 201 }
    )

  } catch (error) {
    console.error("Create session error:", error)
    const message = error instanceof Error ? error.message : "Internal server error"
    return NextResponse.json(
      { error: message },
      { status: 500 }
    )
  }
}
