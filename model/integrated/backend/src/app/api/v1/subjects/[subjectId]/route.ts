import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/subjects/[subjectId] — get single subject with details
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId } = await params

    const subject = await prisma.subject.findUnique({
      where: { id: subjectId },
      include: {
        semesterCriteria: {
          orderBy: { order: "asc" }
        },
        sessions: {
          orderBy: { date: "desc" }
        }
      }
    })

    if (!subject) {
      return NextResponse.json(
        { error: "Subject not found" },
        { status: 404 }
      )
    }

    // Make sure teacher owns this subject
    if (subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    return NextResponse.json({ subject }, { status: 200 })

  } catch (error) {
    console.error("Get subject error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// PATCH /api/v1/subjects/[subjectId] — update subject
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId } = await params
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    const { name, description } = body

    if (
      (name !== undefined && (typeof name !== "string" || !name.trim())) ||
      (description !== undefined && description !== null && typeof description !== "string")
    ) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    // Check subject exists and teacher owns it
    const existing = await prisma.subject.findUnique({
      where: { id: subjectId }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Subject not found" },
        { status: 404 }
      )
    }

    if (existing.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    const subject = await prisma.subject.update({
      where: { id: subjectId },
      data: {
        name: name !== undefined ? name.trim() : existing.name,
        description: description !== undefined ? description?.trim() || null : existing.description
      }
    })

    return NextResponse.json(
      { success: true, subject },
      { status: 200 }
    )

  } catch (error) {
    console.error("Update subject error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// DELETE /api/v1/subjects/[subjectId] — delete subject
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId } = await params

    // Check subject exists and teacher owns it
    const existing = await prisma.subject.findUnique({
      where: { id: subjectId }
    })

    if (!existing) {
      return NextResponse.json(
        { error: "Subject not found" },
        { status: 404 }
      )
    }

    if (existing.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    await prisma.subject.delete({
      where: { id: subjectId }
    })

    return NextResponse.json(
      { success: true },
      { status: 200 }
    )

  } catch (error) {
    console.error("Delete subject error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
