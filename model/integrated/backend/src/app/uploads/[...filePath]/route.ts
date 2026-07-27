import { NextRequest, NextResponse } from "next/server"
import { readFile, stat } from "fs/promises"
import path from "path"

const CONTENT_TYPES: Record<string, string> = {
  ".pdf": "application/pdf",
  ".ppt": "application/vnd.ms-powerpoint",
  ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".txt": "text/plain; charset=utf-8"
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ filePath: string[] }> }
) {
  const { filePath } = await params
  const uploadRoot = path.resolve(process.cwd(), process.env.UPLOAD_PATH ?? "uploads")
  const resolvedPath = path.resolve(uploadRoot, ...filePath)

  if (resolvedPath !== uploadRoot && !resolvedPath.startsWith(uploadRoot + path.sep)) {
    return NextResponse.json({ error: "Invalid upload path" }, { status: 400 })
  }

  try {
    const fileStat = await stat(resolvedPath)

    if (!fileStat.isFile()) {
      return NextResponse.json({ error: "File not found" }, { status: 404 })
    }

    const file = await readFile(resolvedPath)
    const contentType = CONTENT_TYPES[path.extname(resolvedPath).toLowerCase()] ?? "application/octet-stream"

    return new NextResponse(new Uint8Array(file), {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Length": String(file.length),
        "Content-Disposition": `inline; filename="${path.basename(resolvedPath).replace(/"/g, "")}"`
      }
    })
  } catch {
    return NextResponse.json({ error: "File not found" }, { status: 404 })
  }
}
