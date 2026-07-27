import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ summaryId: string }> },
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const userRole = request.headers.get("x-user-role")
    const { summaryId } = await params
    const body = await request.json()
    const { topic, explanation, example, teachingAction, priority = "medium" } = body ?? {}

    if (
      userRole !== "TEACHER" ||
      typeof teacherId !== "string" ||
      typeof topic !== "string" ||
      !topic.trim() ||
      typeof explanation !== "string" ||
      !explanation.trim()
    ) {
      return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 })
    }

    const summary = await prisma.nextClassFeedbackSummary.findUnique({
      where: { id: summaryId },
      include: {
        preview: { select: { subjectId: true } },
      },
    })

    if (!summary) {
      return NextResponse.json({ error: "Summary not found" }, { status: 404 })
    }

    const subject = await prisma.subject.findUnique({
      where: { id: summary.preview.subjectId },
      select: { teacherId: true },
    })

    if (!subject || subject.teacherId !== teacherId) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const note = await prisma.teacherRevisionNote.create({
      data: {
        summaryId,
        nextSessionId: summary.nextSessionId,
        topic: topic.trim(),
        explanation: explanation.trim(),
        example: typeof example === "string" && example.trim() ? example.trim() : null,
        teachingAction:
          typeof teachingAction === "string" && teachingAction.trim()
            ? teachingAction.trim()
            : null,
        priority: ["low", "medium", "high"].includes(priority) ? priority : "medium",
        createdById: teacherId,
      },
    })

    return NextResponse.json({ note }, { status: 201 })
  } catch (error) {
    console.error("Create revision note error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
