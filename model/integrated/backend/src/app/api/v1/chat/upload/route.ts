import { NextRequest, NextResponse } from "next/server"
import { mkdir, writeFile } from "fs/promises"
import path from "path"
import { checkChatRateLimit, ensureActiveSession, sendChatMessageWithAttachment } from "@/lib/chat"
import { prisma } from "@/lib/prisma"

const MAX_UPLOAD_SIZE = 10 * 1024 * 1024

// POST /api/v1/chat/upload — upload a chat image/PDF and send it to the agent
export async function POST(request: NextRequest) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const language = request.headers.get("x-user-language") ?? "en"
    const formData = await request.formData()
    const sessionId = formData.get("sessionId")
    const message = formData.get("message")
    const file = formData.get("file")

    if (typeof sessionId !== "string" || !(file instanceof File)) {
      return NextResponse.json({ error: "Missing required fields or file" }, { status: 400 })
    }

    if (message !== null && typeof message !== "string") {
      return NextResponse.json({ error: "Invalid message" }, { status: 400 })
    }

    if (!file.type.startsWith("image/") && file.type !== "application/pdf") {
      return NextResponse.json({ error: "Only images and PDF files are allowed" }, { status: 400 })
    }

    if (file.size > MAX_UPLOAD_SIZE) {
      return NextResponse.json({ error: "File size must be less than 10MB" }, { status: 413 })
    }

    if (!(await checkChatRateLimit(studentId))) {
      return NextResponse.json({ error: "Rate limit exceeded" }, { status: 429 })
    }

    const sessionResult = await ensureActiveSession(sessionId)
    if (!sessionResult.ok) {
      return NextResponse.json({ error: sessionResult.error }, { status: sessionResult.status })
    }

    const safeOriginalName = path.basename(file.name)
      .replace(/[^a-zA-Z0-9._-]/g, "-")
      .replace(/^-+|-+$/g, "")

    if (!safeOriginalName) {
      return NextResponse.json({ error: "Invalid file name" }, { status: 400 })
    }

    const uploadDir = path.join(
      path.resolve(process.cwd(), process.env.UPLOAD_PATH ?? "uploads"),
      "chat",
      sessionId,
      studentId
    )
    const storedFileName = `${Date.now()}-${safeOriginalName}`
    const fileUrl = `/uploads/chat/${sessionId}/${studentId}/${storedFileName}`
    const fileBuffer = Buffer.from(await file.arrayBuffer())
    const forwardedFile = new File([fileBuffer], file.name, { type: file.type })
    await mkdir(uploadDir, { recursive: true })
    await writeFile(path.join(uploadDir, storedFileName), fileBuffer)

    const studentMessage = message?.trim() || `Uploaded ${file.name}`
    const chatResult = await sendChatMessageWithAttachment({
      studentId,
      language,
      sessionId,
      message: studentMessage,
      file: forwardedFile
    })

    if (!chatResult.ok) {
      return NextResponse.json({ error: chatResult.error }, { status: chatResult.status })
    }

    await prisma.chatImageLog.create({
      data: {
        studentId,
        sessionId,
        messageId: chatResult.studentMessageId,
        imageUrl: fileUrl,
        materialId: null,
        pageNumber: null
      }
    })

    return NextResponse.json(
      {
        success: true,
        messageId: chatResult.studentMessageId,
        fileUrl,
        fileType: file.type,
        response: chatResult.response,
        phase: chatResult.phase,
        language: chatResult.language,
        references: chatResult.references,
        flaggedCriteria: chatResult.flaggedCriteria
      },
      { status: 201 }
    )
  } catch (error) {
    console.error("Chat upload error:", error)
    const message = error instanceof Error ? error.message : "Internal server error"
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
