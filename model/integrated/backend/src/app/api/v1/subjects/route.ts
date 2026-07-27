import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/subjects — get all subjects for current teacher
export async function GET(request: NextRequest) {
  try {
    const teacherId = request.headers.get("x-user-id")

    const subjects = await prisma.subject.findMany({
      where: { teacherId: teacherId! },
      include: {
        _count: {
          select: {
            sessions: true,
            semesterCriteria: true
          }
        }
      },
      orderBy: { createdAt: "desc" }
    })

    return NextResponse.json({ subjects }, { status: 200 })

  } catch (error) {
    console.error("Get subjects error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// POST /api/v1/subjects — create a new subject
export async function POST(request: NextRequest) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Subject name is required" }, { status: 400 })
    }

    const { name, description } = body

    // Validate required fields
    if (typeof name !== "string" || !name.trim() ||
      (description !== undefined && description !== null && typeof description !== "string")) {
      return NextResponse.json(
        { error: "Subject name is required" },
        { status: 400 }
      )
    }

    const subject = await prisma.subject.create({
      data: {
        name: name.trim(),
        description: description?.trim() || null,
        teacherId: teacherId!
      }
    })

    return NextResponse.json(
      { success: true, subject },
      { status: 201 }
    )

  } catch (error) {
    console.error("Create subject error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
