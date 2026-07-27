import { NextRequest, NextResponse } from "next/server"
import { getPreviewForTeacher, regeneratePreviewQuestions } from "@/lib/next-class-readiness"

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

    if (preview.status !== "DRAFT") {
      return NextResponse.json({ error: "Only draft previews can regenerate questions" }, { status: 409 })
    }

    const questions = await regeneratePreviewQuestions(previewId)
    return NextResponse.json({ previewId, questions }, { status: 200 })
  } catch (error) {
    console.error("Generate next-class questions error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
