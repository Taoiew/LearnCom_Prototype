import { NextRequest, NextResponse } from "next/server"
import { checkChatRateLimit, sendChatMessage } from "@/lib/chat"

// POST /api/v1/chat — send a student message to the learning agent
export async function POST(request: NextRequest) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const language = request.headers.get("x-user-language") ?? "en"
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
    }

    const { sessionId, message } = body
    if (typeof sessionId !== "string" || typeof message !== "string" || !message.trim()) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
    }

    if (!(await checkChatRateLimit(studentId))) {
      return NextResponse.json({ error: "Rate limit exceeded" }, { status: 429 })
    }

    const result = await sendChatMessage({
      studentId,
      language,
      sessionId,
      message: message.trim()
    })

    if (!result.ok) {
      return NextResponse.json({ error: result.error }, { status: result.status })
    }

    return NextResponse.json(
      {
        response: result.response,
        phase: result.phase,
        language: result.language,
        conversationId: result.conversationId,
        references: result.references,
        flaggedCriteria: result.flaggedCriteria
      },
      { status: 200 }
    )
  } catch (error) {
    console.error("Chat error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
