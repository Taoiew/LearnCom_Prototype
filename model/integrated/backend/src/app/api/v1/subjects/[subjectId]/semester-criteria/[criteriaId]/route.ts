import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// PATCH /api/v1/subjects/[subjectId]/semester-criteria/[criteriaId]
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string; criteriaId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId, criteriaId } = await params
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    const { description, goal, order } = body

    if (
      (description === undefined && goal === undefined && order === undefined) ||
      (description !== undefined && (typeof description !== "string" || !description.trim())) ||
      (goal !== undefined && (typeof goal !== "string" || !goal.trim())) ||
      (order !== undefined && (!Number.isInteger(order) || order < 0))
    ) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
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

    // Check criteria exists
    const existing = await prisma.semesterCriteria.findUnique({
      where: { id: criteriaId }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    if (existing.subjectId !== subjectId) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    const criteria = await prisma.semesterCriteria.update({
      where: { id: criteriaId },
      data: {
        description: description !== undefined ? description.trim() : existing.description,
        goal: goal !== undefined ? goal.trim() : existing.goal,
        order: order !== undefined ? order : existing.order
      }
    })

    return NextResponse.json(
      { success: true, criteria },
      { status: 200 }
    )

  } catch (error) {
    console.error("Update semester criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// DELETE /api/v1/subjects/[subjectId]/semester-criteria/[criteriaId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string; criteriaId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId, criteriaId } = await params

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

    // Check criteria exists
    const existing = await prisma.semesterCriteria.findUnique({
      where: { id: criteriaId }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    if (existing.subjectId !== subjectId) {
      return NextResponse.json(
        { error: "Criteria not found" },
        { status: 404 }
      )
    }

    await prisma.semesterCriteria.delete({
      where: { id: criteriaId }
    })

    return NextResponse.json(
      { success: true },
      { status: 200 }
    )

  } catch (error) {
    console.error("Delete semester criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
