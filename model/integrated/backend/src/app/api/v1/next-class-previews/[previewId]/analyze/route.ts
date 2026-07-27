import { NextRequest, NextResponse } from "next/server"
import { analyzePreview, getPreviewForTeacher } from "@/lib/next-class-readiness"

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

    const summary = await analyzePreview(previewId)
    return NextResponse.json({ summary }, { status: 200 })
  } catch (error) {
    console.error("Analyze next-class preview error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
