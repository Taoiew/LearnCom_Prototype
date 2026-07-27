import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"
import { getPreviewForTeacher } from "@/lib/next-class-readiness"

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ previewId: string }> },
) {
  try {
    const { previewId } = await params
    const preview = await getPreviewForTeacher(previewId, request.headers.get("x-user-id"))

    if (!preview) {
      return NextResponse.json({ error: "Preview not found" }, { status: 404 })
    }

    if (preview.questions.length === 0) {
      return NextResponse.json({ error: "Generate questions before publishing" }, { status: 400 })
    }

    const updated = await prisma.nextClassPreview.update({
      where: { id: previewId },
      data: { status: "PUBLISHED", publishedAt: new Date() },
      include: {
        questions: { orderBy: { order: "asc" } },
        summary: { include: { revisionNotes: true } },
      },
    })

    return NextResponse.json({ preview: updated }, { status: 200 })
  } catch (error) {
    console.error("Publish next-class preview error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
