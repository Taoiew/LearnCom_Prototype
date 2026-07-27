import { NextRequest, NextResponse } from "next/server"
import { generateSessionReport } from "@/lib/reports"

// POST /api/v1/reports/trigger/[sessionId] — generate or refresh a completed session report
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")!
    const { sessionId } = await params
    const result = await generateSessionReport(sessionId, teacherId)

    if (!result.ok) {
      return NextResponse.json({ error: result.error }, { status: result.status })
    }

    return NextResponse.json(
      { success: true, message: "Report generated", reportId: result.report.id },
      { status: 200 }
    )
  } catch (error) {
    console.error("Generate session report error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
