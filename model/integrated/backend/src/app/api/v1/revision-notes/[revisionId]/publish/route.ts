import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ revisionId: string }> },
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { revisionId } = await params

    const note = await prisma.teacherRevisionNote.findUnique({
      where: { id: revisionId },
      include: {
        summary: {
          include: {
            preview: { select: { subjectId: true } },
          },
        },
      },
    })

    if (!note) {
      return NextResponse.json({ error: "Revision note not found" }, { status: 404 })
    }

    const subject = await prisma.subject.findUnique({
      where: { id: note.summary.preview.subjectId },
      select: { teacherId: true },
    })

    if (!subject || subject.teacherId !== teacherId) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const updated = await prisma.teacherRevisionNote.update({
      where: { id: revisionId },
      data: { isPublished: true },
    })

    return NextResponse.json({ note: updated }, { status: 200 })
  } catch (error) {
    console.error("Publish revision note error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
