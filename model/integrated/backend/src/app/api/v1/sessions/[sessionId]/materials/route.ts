import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"
import { writeFile, mkdir } from "fs/promises"
import path from "path"
import { uploadAndProcessMaterialWithModel } from "@/lib/ai"

// GET /api/v1/sessions/[sessionId]/materials
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const userId = request.headers.get("x-user-id")
    const userRole = request.headers.get("x-user-role")
    const { sessionId } = await params

    // Check session exists and caller has access
    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: { teacherId: true }
        }
      }
    })

    if (!session) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    if (userRole === "TEACHER" && session.subject.teacherId !== userId) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    if (userRole === "STUDENT" && session.status !== "ACTIVE") {
      return NextResponse.json({ error: "Session is not active" }, { status: 403 })
    }

    const materials = await prisma.material.findMany({
      where: { sessionId },
      orderBy: { uploadedAt: "desc" }
    })

    return NextResponse.json({ materials }, { status: 200 })

  } catch (error) {
    console.error("Get materials error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// POST /api/v1/sessions/[sessionId]/materials
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId } = await params

    // Check session exists and teacher owns it
    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: {
        subject: {
          select: { teacherId: true }
        }
      }
    })

    if (!session) {
      return NextResponse.json(
        { error: "Session not found" },
        { status: 404 }
      )
    }

    if (session.subject.teacherId !== teacherId) {
      return NextResponse.json(
        { error: "Access denied" },
        { status: 403 }
      )
    }

    // Parse form data
    const formData = await request.formData()
    const file = formData.get("file")

    if (!(file instanceof File)) {
      return NextResponse.json(
        { error: "No file uploaded" },
        { status: 400 }
      )
    }

    // Validate file type
    const allowedTypes = [
      "application/pdf",
      "application/vnd.ms-powerpoint",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ]

    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: "Only PDF and PowerPoint files are allowed" },
        { status: 400 }
      )
    }

    // Validate file size — max 50MB
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: "File size must be less than 50MB" },
        { status: 413 }
      )
    }

    // Create upload directory
    const uploadDir = path.join(
      path.resolve(process.cwd(), process.env.UPLOAD_PATH ?? "uploads"),
      "materials",
      sessionId
    )
    await mkdir(uploadDir, { recursive: true })

    // Save file
    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)
    const safeOriginalName = path.basename(file.name)
      .replace(/[^a-zA-Z0-9._-]/g, "-")
      .replace(/^-+|-+$/g, "")

    if (!safeOriginalName) {
      return NextResponse.json(
        { error: "Invalid file name" },
        { status: 400 }
      )
    }

    const fileName = `${Date.now()}-${safeOriginalName}`
    const filePath = path.join(uploadDir, fileName)
    await writeFile(filePath, buffer)

    const modelProcessing = await uploadAndProcessMaterialWithModel(file, {
      courseId: session.subjectId,
      classSessionId: session.id
    })

    // Store in database
    const fileUrl = `/uploads/materials/${sessionId}/${fileName}`
    const material = await prisma.material.create({
      data: {
        sessionId,
        fileName: file.name,
        fileUrl,
        fileType: file.type,
        isProcessed: modelProcessing.ok
      }
    })

    return NextResponse.json(
      { success: true, material, modelProcessing },
      { status: 201 }
    )

  } catch (error) {
    console.error("Upload material error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
