import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/reports/materials/[sessionId] — aggregate material/page references from chat uploads
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")!
    const { sessionId } = await params
    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: { subject: { select: { teacherId: true } } }
    })
    if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 })
    if (session.subject.teacherId !== teacherId) return NextResponse.json({ error: "Access denied" }, { status: 403 })

    const imageLogs = await prisma.chatImageLog.findMany({
      where: { sessionId },
      include: { material: { select: { id: true, fileName: true } } }
    })
    const messages = await prisma.message.findMany({
      where: { id: { in: imageLogs.map((log) => log.messageId) } },
      select: { id: true, content: true }
    })
    const messageContent = new Map(messages.map((message) => [message.id, message.content]))
    const grouped = new Map<string, {
      materialId: string
      fileName: string
      totalReferences: number
      pages: Map<number, { references: number; context: string }>
    }>()

    for (const log of imageLogs) {
      if (!log.material) continue
      const materialGroup = grouped.get(log.material.id) ?? {
        materialId: log.material.id,
        fileName: log.material.fileName,
        totalReferences: 0,
        pages: new Map()
      }
      materialGroup.totalReferences += 1
      if (log.pageNumber) {
        const page = materialGroup.pages.get(log.pageNumber) ?? { references: 0, context: "" }
        page.references += 1
        page.context ||= messageContent.get(log.messageId) ?? "Referenced by student image upload"
        materialGroup.pages.set(log.pageNumber, page)
      }
      grouped.set(log.material.id, materialGroup)
    }

    const materials = [...grouped.values()]
      .sort((a, b) => b.totalReferences - a.totalReferences)
      .map((material) => ({
        materialId: material.materialId,
        fileName: material.fileName,
        totalReferences: material.totalReferences,
        pages: [...material.pages.entries()]
          .map(([pageNumber, page]) => ({ pageNumber, ...page }))
          .sort((a, b) => b.references - a.references)
      }))

    return NextResponse.json({ sessionId, totalImagesSent: imageLogs.length, materials })
  } catch (error) {
    console.error("Get material report error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
