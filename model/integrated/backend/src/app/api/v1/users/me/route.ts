import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/prisma"

const profileFields = {
  id: true,
  name: true,
  email: true,
  role: true,
  language: true,
  createdAt: true
} as const

// GET /api/v1/users/me — get the authenticated user's profile
export async function GET(request: NextRequest) {
  try {
    const userId = request.headers.get("x-user-id")

    const user = await prisma.user.findUnique({
      where: { id: userId! },
      select: profileFields
    })

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    return NextResponse.json(user, { status: 200 })
  } catch (error) {
    console.error("Get current user error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}

// PATCH /api/v1/users/me — update the authenticated user's editable profile fields
export async function PATCH(request: NextRequest) {
  try {
    const userId = request.headers.get("x-user-id")
    const body = await request.json()

    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    const { name, language, ...unknownFields } = body

    if (
      Object.keys(unknownFields).length > 0 ||
      (name === undefined && language === undefined) ||
      (name !== undefined && (typeof name !== "string" || !name.trim())) ||
      (language !== undefined && !["en", "th"].includes(language))
    ) {
      return NextResponse.json({ error: "Invalid fields" }, { status: 400 })
    }

    const existingUser = await prisma.user.findUnique({
      where: { id: userId! },
      select: { id: true }
    })

    if (!existingUser) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    const user = await prisma.user.update({
      where: { id: existingUser.id },
      data: {
        ...(name !== undefined && { name: name.trim() }),
        ...(language !== undefined && { language })
      },
      select: profileFields
    })

    return NextResponse.json({ success: true, user }, { status: 200 })
  } catch (error) {
    console.error("Update current user error:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
