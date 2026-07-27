import { NextRequest, NextResponse } from "next/server"
import { getPreviewForTeacher, serializePreview } from "@/lib/next-class-readiness"

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ previewId: string }> },
) {
  try {
    const { previewId } = await params
    const preview = await getPreviewForTeacher(previewId, request.headers.get("x-user-id"))

    if (!preview) {
      return NextResponse.json({ error: "Preview not found" }, { status: 404 })
    }

    return NextResponse.json({ preview: serializePreview(preview) }, { status: 200 })
  } catch (error) {
    console.error("Get next-class preview error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
