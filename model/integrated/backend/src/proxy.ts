import { NextRequest, NextResponse } from "next/server"
import { verifyToken, getTokenFromRequest } from "@/lib/auth"

// Routes that don't need authentication
const publicRoutes = [
  "/api/v1/auth/register",
  "/api/v1/auth/login"
]

// Routes that only teachers can access
const teacherOnlyRoutes = [
  "/api/v1/subjects",
  "/api/v1/reports/trigger",
  "/api/v1/reports/session",
  "/api/v1/reports/weekly",
  "/api/v1/reports/materials"
]

// Routes that only students can access
const studentOnlyRoutes = [
  "/api/v1/chat",
  "/api/v1/quiz",
  "/api/v1/attendance"
]

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public routes
  if (publicRoutes.some((route) => pathname.startsWith(route))) {
    return NextResponse.next()
  }

  // Internal ingestion routes authenticate with a server-to-server secret,
  // not a user JWT.
  if (pathname === "/api/v1/training/store") {
    const internalSecret = process.env.INTERNAL_API_SECRET
    if (!internalSecret || request.headers.get("x-internal-api-secret") !== internalSecret) {
      return NextResponse.json({ error: "Access denied" }, { status: 403 })
    }
    return NextResponse.next()
  }

  // Get and verify token
  const token = getTokenFromRequest(request)

  if (!token) {
    return NextResponse.json(
      { error: "Not authenticated" },
      { status: 401 }
    )
  }

  const user = verifyToken(token)

  if (!user) {
    return NextResponse.json(
      { error: "Invalid or expired token" },
      { status: 401 }
    )
  }

  const isStudentSessionRead =
    request.method === "GET" &&
    /^\/api\/v1\/sessions(?:\/[^/]+)?(?:\/materials)?\/?$/.test(pathname)

  if (pathname.startsWith("/api/v1/sessions") && user.role === "STUDENT" && !isStudentSessionRead) {
    return NextResponse.json(
      { error: "Access denied — teachers only" },
      { status: 403 }
    )
  }

  if (pathname.startsWith("/api/v1/sessions") && user.role !== "STUDENT" && user.role !== "TEACHER") {
    return NextResponse.json(
      { error: "Access denied" },
      { status: 403 }
    )
  }

  if (pathname.startsWith("/api/v1/reports/student") && user.role !== "STUDENT" && user.role !== "TEACHER") {
    return NextResponse.json(
      { error: "Access denied" },
      { status: 403 }
    )
  }

  // Check teacher only routes
  if (teacherOnlyRoutes.some((route) => pathname.startsWith(route))) {
    if (user.role !== "TEACHER") {
      return NextResponse.json(
        { error: "Access denied — teachers only" },
        { status: 403 }
      )
    }
  }

  // Check student only routes
  if (studentOnlyRoutes.some((route) => pathname.startsWith(route))) {
    if (user.role !== "STUDENT") {
      return NextResponse.json(
        { error: "Access denied — students only" },
        { status: 403 }
      )
    }
  }

  // Attach user info to request headers for routes to use
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set("x-user-id", user.id)
  requestHeaders.set("x-user-role", user.role)
  requestHeaders.set("x-user-name", user.name)
  requestHeaders.set("x-user-language", user.language)
  requestHeaders.set("x-user-email", user.email)

  return NextResponse.next({
    request: {
      headers: requestHeaders
    }
  })
}

export const config = {
  matcher: ["/api/v1/:path*"]
}
