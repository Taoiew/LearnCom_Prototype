import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/reports/session/[sessionId] — get a teacher's full session report
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")!
    const { sessionId } = await params
    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      include: { subject: { select: { teacherId: true } } }
    })

    if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 })
    if (session.subject.teacherId !== teacherId) return NextResponse.json({ error: "Access denied" }, { status: 403 })

    const report = await prisma.sessionReport.findUnique({
      where: { sessionId },
      include: { studentReports: { include: { student: { select: { id: true, name: true } } } } }
    })
    if (!report) return NextResponse.json({ error: "Report not found yet" }, { status: 404 })

    return NextResponse.json({
      sessionId,
      avgReadiness: report.avgReadiness,
      studentCount: report.studentCount,
      weakCriteria: report.weakCriteria,
      mostAskedTopics: report.mostAskedTopics,
      aiInsight: report.aiInsight,
      students: report.studentReports.map((studentReport) => ({
        studentId: studentReport.student.id,
        name: studentReport.student.name,
        readinessScore: studentReport.readinessScore,
        readiness: studentReport.readinessScore >= 80 ? "READY" : studentReport.readinessScore >= 50 ? "PARTIAL" : "NOT_READY",
        caughtUp: studentReport.caughtUp,
        duringClassQCount: studentReport.duringClassQCount,
        weakCriteria: studentReport.weakCriteria
      })),
      generatedAt: report.generatedAt
    })
  } catch (error) {
    console.error("Get session report error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
