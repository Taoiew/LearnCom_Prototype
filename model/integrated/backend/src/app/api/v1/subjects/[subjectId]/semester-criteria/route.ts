import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/subjects/[subjectId]/semester-criteria
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId } = await params

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

    const semesterCriteria = await prisma.semesterCriteria.findMany({
      where: { subjectId },
      orderBy: { order: "asc" }
    })

    return NextResponse.json({ semesterCriteria }, { status: 200 })

  } catch (error) {
    console.error("Get semester criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// POST /api/v1/subjects/[subjectId]/semester-criteria
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { subjectId } = await params
    const body = await request.json()
    const { description, goal, order } = body

    // Validate required fields
    if (!description || !goal || order === undefined) {
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

    const criteria = await prisma.semesterCriteria.create({
      data: {
        subjectId,
        description,
        goal,
        order
      }
    })

    return NextResponse.json(
      { success: true, criteria },
      { status: 201 }
    )

  } catch (error) {
    console.error("Create semester criteria error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}