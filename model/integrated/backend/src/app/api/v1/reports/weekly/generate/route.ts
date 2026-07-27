import { NextRequest, NextResponse } from "next/server"
import { callAIWeeklySummary } from "@/lib/ai"
import { prisma } from "@/lib/prisma"

// POST /api/v1/reports/weekly/generate — generate a weekly subject summary
export async function POST(request: NextRequest) {
  try {
    const teacherId = request.headers.get("x-user-id")!
    const body = await request.json()
    const { subjectId, weekNumber, weekStart, weekEnd } = body ?? {}
    const start = new Date(weekStart)
    const end = new Date(weekEnd)

    if (
      typeof subjectId !== "string" || !Number.isInteger(weekNumber) || weekNumber < 1 ||
      typeof weekStart !== "string" || typeof weekEnd !== "string" ||
      Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || start > end
    ) {
      return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 })
    }

    const subject = await prisma.subject.findUnique({ where: { id: subjectId } })
    if (!subject) return NextResponse.json({ error: "Subject not found" }, { status: 404 })
    if (subject.teacherId !== teacherId) return NextResponse.json({ error: "Access denied" }, { status: 403 })

    const sessions = await prisma.classSession.findMany({
      where: { subjectId, date: { gte: start, lte: end } },
      include: { sessionReport: { include: { studentReports: true } } }
    })
    const reports = sessions.flatMap((session) => session.sessionReport ? [session.sessionReport] : [])
    const avgReadiness = reports.length === 0
      ? 0
      : reports.reduce((sum, report) => sum + report.avgReadiness, 0) / reports.length
    const studentReports = reports.flatMap((report) => report.studentReports)
    const semesterProgress = studentReports.length === 0
      ? 0
      : studentReports.reduce((sum, report) => sum + report.semesterProgressPercent, 0) / studentReports.length
    const aiResult = await callAIWeeklySummary({
      subjectName: subject.name,
      weekNumber,
      avgReadiness,
      semesterProgress
    })

    const existing = await prisma.weeklySummary.findFirst({
      where: { subjectId, weekNumber },
      orderBy: { generatedAt: "desc" }
    })
    const summary = existing
      ? await prisma.weeklySummary.update({
          where: { id: existing.id },
          data: { weekStart: start, weekEnd: end, avgReadiness, semesterProgress, aiSummary: aiResult.summary }
        })
      : await prisma.weeklySummary.create({
          data: { subjectId, weekNumber, weekStart: start, weekEnd: end, avgReadiness, semesterProgress, aiSummary: aiResult.summary }
        })

    return NextResponse.json({ success: true, summary }, { status: 201 })
  } catch (error) {
    console.error("Generate weekly report error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
