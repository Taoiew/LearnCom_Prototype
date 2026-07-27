import bcrypt from "bcryptjs"
import jwt from "jsonwebtoken"

const JWT_SECRET = process.env.NEXTAUTH_SECRET!

export interface JWTPayload {
  id: string
  email: string
  role: string
  name: string
  language: string
}

// Hash password before storing
export const hashPassword = async (password: string): Promise<string> => {
  return bcrypt.hash(password, 12)
}

// Compare plain password with hashed one
export const verifyPassword = async (
  password: string,
  hashedPassword: string
): Promise<boolean> => {
  return bcrypt.compare(password, hashedPassword)
}

// Generate JWT token
export const generateToken = (payload: JWTPayload): string => {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: "7d" })
}

// Verify and decode JWT token
export const verifyToken = (token: string): JWTPayload | null => {
  try {
    return jwt.verify(token, JWT_SECRET) as JWTPayload
  } catch {
    return null
  }
}

// Get token from request headers
export const getTokenFromRequest = (request: Request): string | null => {
  const authHeader = request.headers.get("authorization")
  if (authHeader && authHeader.startsWith("Bearer ")) {
    return authHeader.substring(7)
  }

  // Also check cookies
  const cookieHeader = request.headers.get("cookie")
  if (cookieHeader) {
    const cookies = Object.fromEntries(
      cookieHeader.split(";").map((c) => {
        const [key, ...v] = c.trim().split("=")
        return [key, v.join("=")]
      })
    )
    return cookies["auth-token"] || null
  }

  return null
}

// Get current user from request
export const getCurrentUser = (request: Request): JWTPayload | null => {
  const token = getTokenFromRequest(request)
  if (!token) return null
  return verifyToken(token)
}