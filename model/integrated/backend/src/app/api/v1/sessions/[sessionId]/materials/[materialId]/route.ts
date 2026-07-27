import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"
import { unlink } from "fs/promises"
import path from "path"

// DELETE /api/v1/sessions/[sessionId]/materials/[materialId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string; materialId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")
    const { sessionId, materialId } = await params

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

    // Check material exists
    const material = await prisma.material.findUnique({
      where: { id: materialId }
    })

    if (!material) {
      return NextResponse.json(
        { error: "Material not found" },
        { status: 404 }
      )
    }

    if (material.sessionId !== sessionId) {
      return NextResponse.json(
        { error: "Material not found" },
        { status: 404 }
      )
    }

    const uploadRoot = path.join(
      path.resolve(process.cwd(), process.env.UPLOAD_PATH ?? "uploads"),
      "materials",
      sessionId
    )
    const filePath = path.resolve(process.cwd(), `.${material.fileUrl}`)

    if (!filePath.startsWith(`${uploadRoot}${path.sep}`)) {
      return NextResponse.json(
        { error: "Invalid material file path" },
        { status: 500 }
      )
    }

    // Delete file from local storage. A missing file should not prevent cleanup
    // of its database record, but other file-system failures should.
    try {
      await unlink(filePath)
    } catch (error) {
      const errorCode = (error as NodeJS.ErrnoException).code

      if (errorCode !== "ENOENT") {
        throw error
      }
    }

    // Delete from database
    await prisma.material.delete({
      where: { id: materialId }
    })

    return NextResponse.json(
      { success: true },
      { status: 200 }
    )

  } catch (error) {
    console.error("Delete material error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
