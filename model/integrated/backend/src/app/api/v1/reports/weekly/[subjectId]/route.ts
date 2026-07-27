import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

// GET /api/v1/reports/weekly/[subjectId] — get a teacher's weekly summary
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ subjectId: string }> }
) {
  try {
    const teacherId = request.headers.get("x-user-id")!
    const { subjectId } = await params
    const rawWeek = request.nextUrl.searchParams.get("weekNumber") ?? request.nextUrl.searchParams.get("week")
    const weekNumber = rawWeek ? Number(rawWeek) : undefined
    if (rawWeek && (!Number.isInteger(weekNumber) || weekNumber! < 1)) {
      return NextResponse.json({ error: "Invalid week number" }, { status: 400 })
    }

    const subject = await prisma.subject.findUnique({ where: { id: subjectId } })
    if (!subject) return NextResponse.json({ error: "Subject not found" }, { status: 404 })
    if (subject.teacherId !== teacherId) return NextResponse.json({ error: "Access denied" }, { status: 403 })

    const summary = await prisma.weeklySummary.findFirst({
      where: { subjectId, ...(weekNumber && { weekNumber }) },
      orderBy: { generatedAt: "desc" }
    })
    if (!summary) return NextResponse.json({ error: "No summary found" }, { status: 404 })

    const sessions = await prisma.classSession.findMany({
      where: { subjectId, date: { gte: summary.weekStart, lte: summary.weekEnd } },
      include: { sessionReport: { select: { avgReadiness: true, studentCount: true } } },
      orderBy: { date: "asc" }
    })

    return NextResponse.json({
      subjectId,
      weekNumber: summary.weekNumber,
      weekStart: summary.weekStart,
      weekEnd: summary.weekEnd,
      avgReadiness: summary.avgReadiness,
      semesterProgress: summary.semesterProgress,
      aiSummary: summary.aiSummary,
      sessions: sessions.map((session) => ({
        id: session.id,
        title: session.title,
        avgReadiness: session.sessionReport?.avgReadiness ?? 0,
        studentCount: session.sessionReport?.studentCount ?? 0
      })),
      generatedAt: summary.generatedAt
    })
  } catch (error) {
    console.error("Get weekly report error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
