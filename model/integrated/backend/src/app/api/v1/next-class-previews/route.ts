import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"
import { regeneratePreviewQuestions } from "@/lib/next-class-readiness"

export async function POST(request: NextRequest) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const userRole = request.headers.get("x-user-role")
    const body = await request.json()
    const {
      currentSessionId,
      nextSessionId,
      title,
      previewContent,
      materialIds = [],
      generateQuestions = true,
    } = body ?? {}

    if (
      userRole !== "TEACHER" ||
      typeof teacherId !== "string" ||
      typeof currentSessionId !== "string" ||
      typeof nextSessionId !== "string" ||
      typeof title !== "string" ||
      !title.trim() ||
      typeof previewContent !== "string"
    ) {
      return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 })
    }

    const [currentSession, nextSession] = await Promise.all([
      prisma.classSession.findUnique({
        where: { id: currentSessionId },
        include: { subject: { select: { id: true, teacherId: true } } },
      }),
      prisma.classSession.findUnique({
        where: { id: nextSessionId },
        include: { subject: { select: { id: true, teacherId: true } } },
      }),
    ])

    if (!currentSession || !nextSession) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    if (
      currentSession.subject.teacherId !== teacherId ||
      nextSession.subject.teacherId !== teacherId ||
      currentSession.subjectId !== nextSession.subjectId
    ) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const preview = await prisma.nextClassPreview.create({
      data: {
        currentSessionId,
        nextSessionId,
        subjectId: currentSession.subjectId,
        title: title.trim(),
        previewContent: previewContent.trim(),
        materialIds: Array.isArray(materialIds) ? materialIds : [],
        createdById: teacherId,
      },
    })

    const questions = generateQuestions
      ? await regeneratePreviewQuestions(preview.id)
      : []

    return NextResponse.json({ preview: { ...preview, questions } }, { status: 201 })
  } catch (error) {
    console.error("Create next-class preview error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
