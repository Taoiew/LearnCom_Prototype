import { prisma } from "@/lib/prisma"
import { createHash } from "crypto"
import { readFile } from "fs/promises"
import path from "path"

type PreviewQuestionInput = {
  topic: string
  questionText: string
  choices: string[]
  correctChoiceIndex: number
  misconceptionLabels: Record<string, string>
  materialReferences: Array<{
    materialId: string
    fileName: string
    pageNumber?: number | null
    sourceExcerpt?: string | null
  }>
  order: number
}

type NextClassMaterial = {
  id: string
  fileName: string
  fileUrl: string
}

type MaterialEvidence = {
  materialId: string
  fileName: string
  pageNumber: number | null
  content: string
}

type PreviewWithQuestions = Awaited<ReturnType<typeof getPreviewForTeacher>>

const READY_THRESHOLD = 80
const PARTIAL_THRESHOLD = 60

const normalizeTopic = (value: string) =>
  value
    .replace(/^Explain\s+/i, "")
    .replace(/^Understand\s+/i, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80)

const cleanText = (value: string) =>
  value
    .replace(/\u0e22\u0e09/g, "")
    .replace(/โ€ข/g, "-")
    .replace(/\s+/g, " ")
    .trim()

const shortText = (value: string, maxLength = 220) => {
  const cleaned = cleanText(value)
  if (cleaned.length <= maxLength) return cleaned
  return `${cleaned.slice(0, maxLength).replace(/\s+\S*$/, "")}...`
}

const keywordSet = (value: string) =>
  new Set(
    cleanText(value)
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((word) => word.length > 3)
      .filter((word) => !["this", "that", "with", "from", "session", "material", "class"].includes(word)),
  )

const scoreEvidence = (evidence: MaterialEvidence, topic: string) => {
  const keywords = keywordSet(topic)
  const text = cleanText(evidence.content).toLowerCase()
  let score = 0
  for (const keyword of keywords) {
    if (text.includes(keyword)) score += 1
  }
  return score
}

const modelMaterialIdFromUploadUrl = async (fileUrl: string) => {
  if (!fileUrl.startsWith("/uploads/")) return null

  const uploadRoot = path.resolve(process.cwd(), process.env.UPLOAD_PATH ?? "uploads")
  const relativePath = fileUrl.replace(/^\/uploads\/+/, "").split("/").filter(Boolean)
  const filePath = path.resolve(uploadRoot, ...relativePath)

  if (filePath !== uploadRoot && !filePath.startsWith(uploadRoot + path.sep)) {
    return null
  }

  const file = await readFile(filePath)
  return `material-${createHash("sha256").update(file).digest("hex").slice(0, 16)}`
}

const verifiedKbPaths = (modelMaterialId: string) => {
  const modelRoot = path.resolve(process.cwd(), "..", "..")
  return [
    path.join(modelRoot, "data", "material_processing", modelMaterialId, "verified_kb", "verified_kb.json"),
    path.join(modelRoot, "data", "verified_kb", modelMaterialId, "verified_kb.json"),
  ]
}

const readVerifiedKb = async (material: NextClassMaterial): Promise<MaterialEvidence[]> => {
  const modelMaterialId = await modelMaterialIdFromUploadUrl(material.fileUrl)
  if (!modelMaterialId) return []

  for (const kbPath of verifiedKbPaths(modelMaterialId)) {
    try {
      const raw = await readFile(kbPath, "utf8")
      const parsed = JSON.parse(raw) as {
        records?: Array<{
          material_id?: string
          material_name?: string
          page_number?: number
          content?: string
          text_content?: string
          visual_content?: string
        }>
      }

      return (parsed.records ?? [])
        .map((record) => ({
          materialId: record.material_id ?? modelMaterialId,
          fileName: record.material_name ?? material.fileName,
          pageNumber: typeof record.page_number === "number" ? record.page_number : null,
          content: cleanText([record.content, record.text_content, record.visual_content].filter(Boolean).join(" ")),
        }))
        .filter((record) => record.content.length > 40)
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
        console.warn(`Could not read verified KB for ${material.id}:`, error)
      }
    }
  }

  return []
}

const bestEvidenceForTopic = (evidence: MaterialEvidence[], topic: string, index: number) => {
  if (evidence.length === 0) return null

  const ranked = evidence
    .map((item) => ({ item, score: scoreEvidence(item, topic) }))
    .sort((a, b) => b.score - a.score)

  const useful = ranked.filter((entry) => entry.score > 0)
  return (useful[index % useful.length] ?? ranked[index % ranked.length])?.item ?? null
}

const optionText = (topic: string, evidence: MaterialEvidence | null, materialNames: string[]) => {
  const source = evidence
    ? shortText(evidence.content, 170)
    : materialNames.length
      ? `The next class material files are ${materialNames.join(", ")}.`
      : `The teacher has not uploaded processed material for the next class yet.`

  return [
    source,
    `This topic is only an attendance check-in and does not affect next-class readiness.`,
    `Students should ignore the next class material until after the class ends.`,
    `The preview replaces the teacher's rubric instead of preparing students for it.`,
  ]
}

export async function getPreviewForTeacher(previewId: string, teacherId: string | null) {
  const preview = await prisma.nextClassPreview.findUnique({
    where: { id: previewId },
    include: {
      questions: { orderBy: { order: "asc" } },
      summary: { include: { revisionNotes: { orderBy: { createdAt: "desc" } } } },
    },
  })

  if (!preview) return null

  const subject = await prisma.subject.findUnique({
    where: { id: preview.subjectId },
    select: { teacherId: true },
  })

  if (!subject || subject.teacherId !== teacherId) return null
  return preview
}

export async function getPublishedPreviewForCurrentSession(sessionId: string) {
  return prisma.nextClassPreview.findFirst({
    where: { currentSessionId: sessionId, status: "PUBLISHED" },
    include: {
      questions: { orderBy: { order: "asc" } },
      responses: true,
      summary: { include: { revisionNotes: { where: { isPublished: true } } } },
    },
    orderBy: { publishedAt: "desc" },
  })
}

export async function createDeterministicQuestions(previewId: string): Promise<PreviewQuestionInput[]> {
  const preview = await prisma.nextClassPreview.findUnique({
    where: { id: previewId },
  })
  if (!preview) throw new Error("Preview not found")

  const [criteria, materials] = await Promise.all([
    prisma.sessionCriteria.findMany({
      where: { sessionId: preview.nextSessionId },
      orderBy: { order: "asc" },
      take: 3,
    }),
    prisma.material.findMany({
      where: { sessionId: preview.nextSessionId },
      select: { id: true, fileName: true, fileUrl: true },
      take: 3,
    }),
  ])

  const sourceCriteria = criteria.length > 0
    ? criteria
    : [{
        id: "preview",
        description: preview.title,
        goal: preview.previewContent,
        order: 0,
        sessionId: preview.nextSessionId,
        semesterCriteriaId: null,
      }]

  const materialNames = materials.map((material) => material.fileName)
  const evidenceByMaterial = await Promise.all(materials.map((material) => readVerifiedKb(material)))
  const evidence = evidenceByMaterial.flat()

  return sourceCriteria.slice(0, 3).map((criterion, index) => {
    const topic = normalizeTopic(criterion.description || criterion.goal || preview.title)
    const selectedEvidence = bestEvidenceForTopic(evidence, topic, index)
    const choices = optionText(topic, selectedEvidence, materialNames)
    const materialReferences = selectedEvidence
      ? [{
          materialId: selectedEvidence.materialId,
          fileName: selectedEvidence.fileName,
          pageNumber: selectedEvidence.pageNumber,
          sourceExcerpt: shortText(selectedEvidence.content, 260),
        }]
      : materials.map((material) => ({
          materialId: material.id,
          fileName: material.fileName,
          pageNumber: null,
          sourceExcerpt: null,
        }))

    return {
      topic,
      questionText:
        index === 0
          ? `Based on the next class material, which statement best describes ${topic}?`
          : index === 1
            ? `Which choice is a misconception about ${topic}?`
            : `How should you apply ${topic} when preparing for the next class?`,
      choices,
      correctChoiceIndex: index === 1 ? 1 : 0,
      misconceptionLabels: {
        "1": `${topic.toLowerCase().replace(/\W+/g, "_")}_unrelated`,
        "2": "attendance_confusion",
        "3": "rubric_replacement_confusion",
      },
      materialReferences,
      order: index + 1,
    }
  })
}

export async function regeneratePreviewQuestions(previewId: string) {
  const questions = await createDeterministicQuestions(previewId)

  await prisma.$transaction([
    prisma.nextClassReadinessResponse.deleteMany({ where: { previewId } }),
    prisma.nextClassReadinessQuestion.deleteMany({ where: { previewId } }),
    prisma.nextClassReadinessQuestion.createMany({
      data: questions.map((question) => ({
        previewId,
        topic: question.topic,
        questionText: question.questionText,
        choices: question.choices,
        correctChoiceIndex: question.correctChoiceIndex,
        misconceptionLabels: question.misconceptionLabels,
        materialReferences: question.materialReferences,
        order: question.order,
      })),
    }),
  ])

  return prisma.nextClassReadinessQuestion.findMany({
    where: { previewId },
    orderBy: { order: "asc" },
  })
}

export async function analyzePreview(previewId: string) {
  const preview = await prisma.nextClassPreview.findUnique({
    where: { id: previewId },
    include: {
      questions: { include: { responses: true }, orderBy: { order: "asc" } },
    },
  })
  if (!preview) throw new Error("Preview not found")

  const studentIds = new Set<string>()
  let totalResponses = 0
  let correctResponses = 0

  const topicReadiness = preview.questions.map((question) => {
    const responses = question.responses
    const total = responses.length
    const correct = responses.filter((response) => response.isCorrect).length
    const rate = total === 0 ? 0 : Math.round((correct / total) * 100)
    const wrongCounts = new Map<number, number>()

    for (const response of responses) {
      studentIds.add(response.studentId)
      totalResponses += 1
      if (response.isCorrect) correctResponses += 1
      if (!response.isCorrect) {
        wrongCounts.set(
          response.selectedChoiceIndex,
          (wrongCounts.get(response.selectedChoiceIndex) ?? 0) + 1,
        )
      }
    }

    const commonWrong = [...wrongCounts.entries()].sort((a, b) => b[1] - a[1])[0]
    const labels = question.misconceptionLabels as Record<string, string>

    return {
      questionId: question.id,
      topic: question.topic,
      totalResponses: total,
      correctResponses: correct,
      correctRate: rate,
      status: rate >= READY_THRESHOLD
        ? "ready"
        : rate >= PARTIAL_THRESHOLD
          ? "partially_ready"
          : "needs_review",
      commonWrongChoiceIndex: commonWrong?.[0] ?? null,
      commonMisconception: commonWrong ? labels[String(commonWrong[0])] ?? null : null,
    }
  })

  const weakTopics = topicReadiness
    .filter((topic) => topic.status !== "ready")
    .map((topic) => topic.topic)
  const misconceptions = topicReadiness
    .map((topic) => topic.commonMisconception)
    .filter((value): value is string => Boolean(value))
  const overallReadinessScore = totalResponses === 0
    ? 0
    : Math.round((correctResponses / totalResponses) * 100)
  const eligibleStudentCount = Math.max(studentIds.size, 1)

  return prisma.nextClassFeedbackSummary.upsert({
    where: { previewId },
    create: {
      previewId,
      nextSessionId: preview.nextSessionId,
      participationCount: studentIds.size,
      eligibleStudentCount,
      participationRate: studentIds.size / eligibleStudentCount,
      overallReadinessScore,
      topicReadiness,
      commonMisconceptions: misconceptions,
      aiRecommendations: weakTopics.length
        ? weakTopics.slice(0, 3).map((topic) => `Review ${topic} before starting the next class.`)
        : ["Students look ready for the next class preview."],
    },
    update: {
      participationCount: studentIds.size,
      eligibleStudentCount,
      participationRate: studentIds.size / eligibleStudentCount,
      overallReadinessScore,
      topicReadiness,
      commonMisconceptions: misconceptions,
      aiRecommendations: weakTopics.length
        ? weakTopics.slice(0, 3).map((topic) => `Review ${topic} before starting the next class.`)
        : ["Students look ready for the next class preview."],
      generatedAt: new Date(),
    },
    include: { revisionNotes: { orderBy: { createdAt: "desc" } } },
  })
}

export function serializePreview(preview: NonNullable<PreviewWithQuestions>) {
  return {
    id: preview.id,
    currentSessionId: preview.currentSessionId,
    nextSessionId: preview.nextSessionId,
    subjectId: preview.subjectId,
    title: preview.title,
    previewContent: preview.previewContent,
    materialIds: preview.materialIds,
    status: preview.status,
    createdAt: preview.createdAt,
    publishedAt: preview.publishedAt,
    questions: preview.questions,
    summary: preview.summary,
  }
}
