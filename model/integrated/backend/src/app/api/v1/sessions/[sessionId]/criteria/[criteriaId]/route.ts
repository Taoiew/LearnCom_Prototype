import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// PATCH /api/v1/sessions/[sessionId]/criteria/[criteriaId]
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string; criteriaId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId, criteriaId } = await params
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    const { description, goal, order, semesterCriteriaId } = body

    if (
      (description !== undefined && (typeof description !== "string" || !description.trim())) ||
      (goal !== undefined && (typeof goal !== "string" || !goal.trim())) ||
      (order !== undefined && (!Number.isInteger(order) || order < 0)) ||
      (semesterCriteriaId !== undefined && semesterCriteriaId !== null && typeof semesterCriteriaId !== "string")
    ) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    // Check session exists and teacher owns it
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

    if (session.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    // Check criteria exists
    const existing = await prisma.sessionCriteria.findUnique({
      where: { id: criteriaId }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    if (existing.sessionId !== sessionId) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
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

    const criteria = await prisma.sessionCriteria.update({
      where: { id: criteriaId },
      data: {
        description: description !== undefined ? description.trim() : existing.description,
        goal: goal !== undefined ? goal.trim() : existing.goal,
        order: order !== undefined ? order : existing.order,
        semesterCriteriaId: semesterCriteriaId !== undefined
          ? semesterCriteriaId
          : existing.semesterCriteriaId
      }
    })

    return NextResponse.json(
      { success: true, criteria },
      { status: 200 }
    )

  } catch (error) {
    console.error("Update session criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// DELETE /api/v1/sessions/[sessionId]/criteria/[criteriaId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string; criteriaId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId, criteriaId } = await params

    // Check session exists and teacher owns it
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

    if (session.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    // Check criteria exists
    const existing = await prisma.sessionCriteria.findUnique({
      where: { id: criteriaId }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    if (existing.sessionId !== sessionId) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    await prisma.sessionCriteria.delete({
      where: { id: criteriaId }
    })

    return NextResponse.json(
      { success: true },
      { status: 200 }
    )

  } catch (error) {
    console.error("Delete session criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
