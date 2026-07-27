import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// POST /api/v1/chat/image-log — reserved for trusted backend integrations
export async function POST(request: NextRequest) {
  try {
    const internalSecret = process.env.INTERNAL_API_SECRET
    if (!internalSecret || request.headers.get("x-internal-api-secret") !== internalSecret) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const body = await request.json()
    const { studentId, sessionId, messageId, imageUrl, materialId, pageNumber } = body ?? {}

    if (
      typeof studentId !== "string" ||
      typeof sessionId !== "string" ||
      typeof messageId !== "string" ||
      typeof imageUrl !== "string" ||
      (materialId !== undefined && materialId !== null && typeof materialId !== "string") ||
      (pageNumber !== undefined && pageNumber !== null && (!Number.isInteger(pageNumber) || pageNumber < 1))
    ) {
      return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 })
    }

    const imageLog = await prisma.chatImageLog.create({
      data: {
        studentId,
        sessionId,
        messageId,
        imageUrl,
        materialId: materialId ?? null,
        pageNumber: pageNumber ?? null
      }
    })

    return NextResponse.json({ success: true, id: imageLog.id }, { status: 201 })
  } catch (error) {
    console.error("Create image log error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
