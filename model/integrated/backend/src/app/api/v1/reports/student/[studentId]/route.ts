import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/reports/student/[studentId] — student self-view or a teacher's reports for their subjects
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ studentId: string }> }
) {
  try {
    const requesterId = request.headers.get("x-user-id")!
    const requesterRole = request.headers.get("x-user-role")
    const { studentId } = await params

    if (requesterRole === "STUDENT" && requesterId !== studentId) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }

    const student = await prisma.user.findUnique({
      where: { id: studentId },
      select: { id: true, name: true, role: true }
    })
    if (!student || student.role !== "STUDENT") {
      return NextResponse.json({ error: "Student not found" }, { status: 404 })
    }

    const reports = await prisma.studentReport.findMany({
      where: {
        studentId,
        ...(requesterRole === "TEACHER" && {
          sessionReport: { session: { subject: { teacherId: requesterId } } }
        })
      },
      include: {
        sessionReport: {
          include: { session: { select: { id: true, title: true, date: true } } }
        }
      },
      orderBy: { sessionReport: { generatedAt: "desc" } }
    })

    const readinessHistory = reports.map((report) => ({
      sessionId: report.sessionReport.session.id,
      sessionTitle: report.sessionReport.session.title,
      readinessScore: report.readinessScore,
      readiness: report.readinessScore >= 80 ? "READY" : report.readinessScore >= 50 ? "PARTIAL" : "NOT_READY",
      date: report.sessionReport.session.date
    }))
    const weakCriteria = [...new Set(reports.flatMap((report) => Array.isArray(report.weakCriteria) ? report.weakCriteria : []))]
    const semesterProgressPercent = reports.length === 0
      ? 0
      : reports.reduce((sum, report) => sum + report.semesterProgressPercent, 0) / reports.length

    return NextResponse.json({
      studentId: student.id,
      name: student.name,
      readinessHistory,
      weakCriteria,
      semesterProgressPercent,
      totalSessions: reports.length,
      caughtUpCount: reports.filter((report) => report.caughtUp).length
    })
  } catch (error) {
    console.error("Get student report error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
