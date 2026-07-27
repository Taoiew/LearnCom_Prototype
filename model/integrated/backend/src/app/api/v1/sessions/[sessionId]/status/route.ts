import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// Valid phase transitions
const validTransitions: Record<string, { status: string; phase: string }[]> = {
  "UPCOMING-BEFORE": [{ status: "ACTIVE", phase: "BEFORE" }],
  "ACTIVE-BEFORE":   [{ status: "ACTIVE", phase: "DURING" }],
  "ACTIVE-DURING":   [{ status: "ACTIVE", phase: "AFTER" }],
  "ACTIVE-AFTER":    [{ status: "COMPLETED", phase: "AFTER" }]
}

// PATCH /api/v1/sessions/[sessionId]/status
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } = await params
    const body = await request.json()
    const { status, phase } = body

    // Validate required fields
    if (!status || !phase) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      )
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

    // Check valid transition
    const currentKey = `${existing.status}-${existing.phase}`
    const allowedTransitions = validTransitions[currentKey] || []
    const isValid = allowedTransitions.some(
      (t) => t.status === status && t.phase === phase
    )

    if (!isValid) {
      return NextResponse.json(
        {
          error: "Invalid transition",
          current: { status: existing.status, phase: existing.phase },
          allowed: allowedTransitions
        },
        { status: 400 }
      )
    }

    // Update session status and phase
    const session = await prisma.classSession.update({
      where: { id: sessionId },
      data: { status, phase }
    })

    return NextResponse.json(
      { success: true, session },
      { status: 200 }
    )

  } catch (error) {
    console.error("Update session status error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}