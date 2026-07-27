import { NextRequest, NextResponse } from "next/server"
import { ensureActiveSession } from "@/lib/chat"
import { prisma } from "@/lib/prisma"

// GET /api/v1/chat/history/[sessionId] — get the student's current-phase history
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const { sessionId } = await params
    const sessionResult = await ensureActiveSession(sessionId)

    if (!sessionResult.ok) {
      return NextResponse.json({ error: sessionResult.error }, { status: sessionResult.status })
    }

    const conversation = await prisma.conversation.findFirst({
      where: { studentId, sessionId, phase: sessionResult.session.phase },
      include: {
        messages: {
          select: { id: true, role: true, content: true, createdAt: true },
          orderBy: { createdAt: "asc" }
        },
        summary: true
      },
      orderBy: { startedAt: "desc" }
    })
    const messages = conversation?.messages ?? []
    const imageLogs = messages.length
      ? await prisma.chatImageLog.findMany({
          where: {
            studentId,
            sessionId,
            messageId: { in: messages.map((message) => message.id) }
          },
          select: { messageId: true, imageUrl: true }
        })
      : []
    const imageUrlByMessageId = new Map(imageLogs.map((log) => [log.messageId, log.imageUrl]))
    const answerReferences = messages.length
      ? await prisma.answerReference.findMany({
          where: {
            studentId,
            sessionId,
            messageId: { in: messages.map((message) => message.id) }
          },
          orderBy: { createdAt: "asc" }
        })
      : []
    const answerReferencesByMessageId = new Map<string, typeof answerReferences>()
    for (const reference of answerReferences) {
      answerReferencesByMessageId.set(reference.messageId, [
        ...(answerReferencesByMessageId.get(reference.messageId) ?? []),
        reference
      ])
    }

    return NextResponse.json(
      {
        conversationId: conversation?.id ?? null,
        phase: sessionResult.session.phase,
        messages: messages.map((message) => ({
          ...message,
          imageUrl: imageUrlByMessageId.get(message.id) ?? null,
          references: (answerReferencesByMessageId.get(message.id) ?? []).map((reference) => ({
            id: reference.id,
            messageId: reference.messageId,
            studentMessageId: reference.studentMessageId,
            sourceType: reference.sourceType,
            sourceName: reference.sourceName,
            materialId: reference.materialId,
            materialFileName: reference.materialFileName,
            pageNumber: reference.pageNumber,
            sourceQuote: reference.sourceQuote,
            provider: reference.provider,
            createdAt: reference.createdAt
          }))
        })),
        summary: conversation?.summary?.summary ?? ""
      },
      { status: 200 }
    )
  } catch (error) {
    console.error("Get chat history error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
