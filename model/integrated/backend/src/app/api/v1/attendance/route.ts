import { NextRequest, NextResponse } from "next/server"
import { mkdir, writeFile } from "fs/promises"
import path from "path"
import { randomUUID } from "crypto"
import { prisma } from "@/lib/prisma"

const MAX_ATTENDANCE_PHOTO_SIZE = 8 * 1024 * 1024

function sanitizeFileName(name: string) {
  return path.basename(name)
    .replace(/[^a-zA-Z0-9._-]/g, "-")
    .replace(/^-+|-+$/g, "")
}

type AttendanceRow = {
  id: string
  studentId: string
  sessionId: string
  photoUrl: string
  checkedInAt: Date
  sessionTitle: string
  sessionDate: Date
  sessionStatus: string
  subjectName: string | null
}

function mapAttendanceRow(row: AttendanceRow) {
  return {
    id: row.id,
    studentId: row.studentId,
    sessionId: row.sessionId,
    photoUrl: row.photoUrl,
    checkedInAt: row.checkedInAt.toISOString(),
    session: {
      id: row.sessionId,
      title: row.sessionTitle,
      date: row.sessionDate.toISOString(),
      status: row.sessionStatus,
      subject: {
        name: row.subjectName ?? undefined,
      },
    },
  }
}

// GET /api/v1/attendance?sessionId=... - get attendance for current student
export async function GET(request: NextRequest) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const sessionId = request.nextUrl.searchParams.get("sessionId")

    const rows = sessionId
      ? await prisma.$queryRaw<AttendanceRow[]>`
          SELECT
            a."id",
            a."studentId",
            a."sessionId",
            a."photoUrl",
            a."checkedInAt",
            s."title" AS "sessionTitle",
            s."date" AS "sessionDate",
            s."status"::text AS "sessionStatus",
            sub."name" AS "subjectName"
          FROM "Attendance" a
          JOIN "ClassSession" s ON s."id" = a."sessionId"
          LEFT JOIN "Subject" sub ON sub."id" = s."subjectId"
          WHERE a."studentId" = ${studentId} AND a."sessionId" = ${sessionId}
          ORDER BY a."checkedInAt" DESC
        `
      : await prisma.$queryRaw<AttendanceRow[]>`
          SELECT
            a."id",
            a."studentId",
            a."sessionId",
            a."photoUrl",
            a."checkedInAt",
            s."title" AS "sessionTitle",
            s."date" AS "sessionDate",
            s."status"::text AS "sessionStatus",
            sub."name" AS "subjectName"
          FROM "Attendance" a
          JOIN "ClassSession" s ON s."id" = a."sessionId"
          LEFT JOIN "Subject" sub ON sub."id" = s."subjectId"
          WHERE a."studentId" = ${studentId}
          ORDER BY a."checkedInAt" DESC
        `

    return NextResponse.json({ attendances: rows.map(mapAttendanceRow) }, { status: 200 })
  } catch (error) {
    console.error("Get attendance error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

// POST /api/v1/attendance - check in with a photo without AI verification
export async function POST(request: NextRequest) {
  try {
    const studentId = request.headers.get("x-user-id")!
    const formData = await request.formData()
    const sessionId = formData.get("sessionId")
    const file = formData.get("file")

    if (typeof sessionId !== "string" || !(file instanceof File)) {
      return NextResponse.json({ error: "Missing sessionId or photo" }, { status: 400 })
    }

    if (!file.type.startsWith("image/")) {
      return NextResponse.json({ error: "Attendance check-in requires an image file" }, { status: 400 })
    }

    if (file.size > MAX_ATTENDANCE_PHOTO_SIZE) {
      return NextResponse.json({ error: "Photo size must be less than 8MB" }, { status: 413 })
    }

    const session = await prisma.classSession.findUnique({
      where: { id: sessionId },
      select: {
        id: true,
        title: true,
        status: true,
      },
    })

    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 })
    }

    if (session.status !== "ACTIVE") {
      return NextResponse.json({ error: "Attendance can only be checked for active sessions" }, { status: 403 })
    }

    const safeOriginalName = sanitizeFileName(file.name)
    if (!safeOriginalName) {
      return NextResponse.json({ error: "Invalid file name" }, { status: 400 })
    }

    const uploadDir = path.join(
      path.resolve(process.cwd(), process.env.UPLOAD_PATH ?? "uploads"),
      "attendance",
      sessionId,
      studentId,
    )
    const storedFileName = `${Date.now()}-${safeOriginalName}`
    const photoUrl = `/uploads/attendance/${sessionId}/${studentId}/${storedFileName}`
    const fileBuffer = Buffer.from(await file.arrayBuffer())

    await mkdir(uploadDir, { recursive: true })
    await writeFile(path.join(uploadDir, storedFileName), fileBuffer)

    const rows = await prisma.$queryRaw<AttendanceRow[]>`
      INSERT INTO "Attendance" ("id", "studentId", "sessionId", "photoUrl", "checkedInAt")
      VALUES (${`attendance_${randomUUID()}`}, ${studentId}, ${sessionId}, ${photoUrl}, NOW())
      ON CONFLICT ("studentId", "sessionId")
      DO UPDATE SET
        "photoUrl" = EXCLUDED."photoUrl",
        "checkedInAt" = NOW()
      RETURNING
        "id",
        "studentId",
        "sessionId",
        "photoUrl",
        "checkedInAt"
    `

    const attendanceRow = await prisma.$queryRaw<AttendanceRow[]>`
      SELECT
        a."id",
        a."studentId",
        a."sessionId",
        a."photoUrl",
        a."checkedInAt",
        s."title" AS "sessionTitle",
        s."date" AS "sessionDate",
        s."status"::text AS "sessionStatus",
        sub."name" AS "subjectName"
      FROM "Attendance" a
      JOIN "ClassSession" s ON s."id" = a."sessionId"
      LEFT JOIN "Subject" sub ON sub."id" = s."subjectId"
      WHERE a."id" = ${rows[0].id}
      LIMIT 1
    `

    return NextResponse.json({ success: true, attendance: mapAttendanceRow(attendanceRow[0]) }, { status: 201 })
  } catch (error) {
    console.error("Create attendance error:", error)
    const message = error instanceof Error ? error.message : "Internal server error"
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
