export type AIChatMessage = {
  role: "STUDENT" | "AGENT"
  content: string
  createdAt?: Date
}

export type AIAnswerReference = {
  sourceType: "MATERIAL" | "EXTERNAL_AI"
  materialId?: string | null
  materialFileName?: string | null
  pageNumber?: number | null
  sourceQuote?: string | null
  sourceName?: string | null
  provider?: string | null
}

export type AIChatResponse = {
  response: string
  confidence: number
  usedExternalAPI: boolean
  externalSource: string | null
  flaggedCriteria: string[]
  detectedLanguage: "en" | "th"
  references: AIAnswerReference[]
}

type RawAIReference = {
  sourceType?: string
  source_type?: string
  materialId?: string | null
  material_id?: string | null
  materialFileName?: string | null
  material_name?: string | null
  fileName?: string | null
  file_name?: string | null
  pageNumber?: number | null
  page_number?: number | null
  page?: number | null
  sourceQuote?: string | null
  source_quote?: string | null
  quote?: string | null
  sourceName?: string | null
  source_name?: string | null
  provider?: string | null
}

const COURSE_RELEVANCE_STOPWORDS = new Set([
  "what",
  "this",
  "that",
  "about",
  "with",
  "from",
  "using",
  "explain",
  "describe",
  "session",
  "material",
  "course",
  "class",
  "please",
])

const COURSE_KEYWORDS = [
  "aws",
  "cloud",
  "ec2",
  "iam",
  "lambda",
  "vpc",
  "database",
  "storage",
  "network",
  "security",
  "compute",
]

const extractRelevanceTerms = (value: string) => (
  value
    .toLowerCase()
    .normalize("NFKC")
    .match(/[a-z0-9]{3,}|[\u0e00-\u0e7f]{2,}/g) ?? []
).filter((term) => !COURSE_RELEVANCE_STOPWORDS.has(term))

const estimateCourseRelevanceScore = (payload: {
  studentMessage: string
  sessionCriteria: { description: string; goal: string }[]
  teacherMaterial: string
}) => {
  const question = payload.studentMessage.toLowerCase().normalize("NFKC")
  if (
    /what\s+(is\s+)?(this\s+)?(session|course)\s+about/.test(question) ||
    /(summary|summarize|overview|recap)\s+(of|for)?\s*(this\s+)?(session|course|class)/.test(question) ||
    /(this\s+)?(session|course|class)\s+(summary|overview|recap)/.test(question) ||
    /คาบนี้|วิชานี้|บทเรียนนี้|เนื้อหานี้|สรุปคาบ|สรุปบทเรียน|สรุปวิชา|ภาพรวมคาบ|ภาพรวมบทเรียน/.test(question)
  ) {
    return 0.85
  }

  const questionTerms = new Set(extractRelevanceTerms(payload.studentMessage))
  const contextTerms = new Set(
    extractRelevanceTerms([
      payload.teacherMaterial,
      ...payload.sessionCriteria.flatMap((criterion) => [
        criterion.description,
        criterion.goal,
      ]),
    ].join(" "))
  )

  const matchedTerms = [...questionTerms].filter((term) => contextTerms.has(term)).length
  if (matchedTerms >= 2) {
    return 0.9
  }
  if (matchedTerms === 1) {
    return 0.75
  }
  if (COURSE_KEYWORDS.some((keyword) => question.includes(keyword))) {
    return 0.7
  }

  return 0.35
}

export const callAIChat = async (payload: {
  phase: string
  language: string
  studentMessage: string
  recentMessages: AIChatMessage[]
  summary: string
  sessionCriteria: { id: string; description: string; goal: string }[]
  teacherMaterial: string
  studentId?: string
  sessionId?: string
  courseId?: string
  classSessionId?: string
}): Promise<AIChatResponse> => {
  const aiServiceUrl = getAIServiceUrl()
  if (!payload.studentId || !payload.courseId || !payload.classSessionId) {
    throw new Error("Real student, course, and session ids are required for AI chat")
  }

  if (aiServiceUrl) {
    try {
      const response = await fetch(`${aiServiceUrl}/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request: {
            student_id: payload.studentId,
            course_id: payload.courseId,
            class_session_id: payload.classSessionId,
            phase: mapPhaseToModel(payload.phase),
            question: payload.studentMessage,
            conversation_id: payload.sessionId ?? payload.classSessionId
          },
          course_relevance_score: estimateCourseRelevanceScore(payload),
          unsafe: false
        })
      })

      if (response.ok) {
        const body = await response.json() as {
          answer?: string
          confidence?: number
          citations?: RawAIReference[]
          references?: RawAIReference[]
          answer_references?: RawAIReference[]
          used_external_agent?: boolean
        }
        return {
          response: body.answer ?? "The learning companion returned an empty answer.",
          confidence: typeof body.confidence === "number" ? body.confidence : 0.8,
          usedExternalAPI: true,
          externalSource: "python-model-service",
          flaggedCriteria: [],
          detectedLanguage: payload.language === "th" ? "th" : "en",
          references: normalizeAIReferences(
            [...(body.references ?? []), ...(body.citations ?? []), ...(body.answer_references ?? [])],
            "python-model-service",
            body.used_external_agent ?? false
          )
        }
      }

      console.warn("AI chat service returned non-OK status:", response.status, await response.text())
    } catch (error) {
      throw new Error(`AI chat service unavailable: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  throw new Error("AI_SERVICE_URL is not configured")
}

export const callAIChatWithAttachment = async (payload: {
  phase: string
  language: string
  studentMessage: string
  studentId: string
  sessionId: string
  courseId: string
  classSessionId: string
  file: File
}): Promise<AIChatResponse> => {
  const aiServiceUrl = getAIServiceUrl()
  if (!aiServiceUrl) {
    throw new Error("AI_SERVICE_URL is not configured")
  }

  const formData = new FormData()
  formData.append(
    "request_json",
    JSON.stringify({
      student_id: payload.studentId,
      course_id: payload.courseId,
      class_session_id: payload.classSessionId,
      phase: mapPhaseToModel(payload.phase),
      question: payload.studentMessage,
      conversation_id: payload.sessionId
    })
  )
  formData.append("course_relevance_score", "0.9")
  formData.append("unsafe", "false")
  formData.append("file", payload.file, payload.file.name)

  try {
    const response = await fetch(`${aiServiceUrl}/v1/chat/with-attachment`, {
      method: "POST",
      body: formData
    })

    if (!response.ok) {
      throw new Error(await responseError(response))
    }

    const body = await response.json() as {
      chat?: {
        answer?: string
        confidence?: number
        citations?: RawAIReference[]
        references?: RawAIReference[]
        answer_references?: RawAIReference[]
        used_external_agent?: boolean
      }
      citations?: RawAIReference[]
      references?: RawAIReference[]
      answer_references?: RawAIReference[]
    }

    return {
      response: body.chat?.answer ?? "The learning companion returned an empty answer.",
      confidence: typeof body.chat?.confidence === "number" ? body.chat.confidence : 0.8,
      usedExternalAPI: true,
      externalSource: "python-model-service-attachment",
      flaggedCriteria: [],
      detectedLanguage: payload.language === "th" ? "th" : "en",
      references: normalizeAIReferences(
        [
          ...(body.chat?.references ?? []),
          ...(body.chat?.citations ?? []),
          ...(body.chat?.answer_references ?? []),
          ...(body.references ?? []),
          ...(body.citations ?? []),
          ...(body.answer_references ?? [])
        ],
        "python-model-service-attachment",
        body.chat?.used_external_agent ?? false
      )
    }
  } catch (error) {
    throw new Error(`AI attachment chat service unavailable: ${error instanceof Error ? error.message : String(error)}`)
  }
}

export type MaterialProcessingBridgeResult = {
  ok: boolean
  modelMaterialId?: string
  activationStatus?: "activated" | "skipped" | "failed"
  activeMaterialIds?: string[]
  processingStatus?: string
  totalPages?: number
  totalVisionRequests?: number
  totalVisionResponses?: number
  verifiedCount?: number
  needsReviewCount?: number
  rejectedCount?: number
  error?: string
}

export const uploadAndProcessMaterialWithModel = async (
  file: File,
  scope?: { courseId: string; classSessionId: string }
): Promise<MaterialProcessingBridgeResult> => {
  const aiServiceUrl = getAIServiceUrl()
  if (!aiServiceUrl) {
    return {
      ok: false,
      error: "AI_SERVICE_URL is not configured"
    }
  }

  try {
    const formData = new FormData()
    formData.append("file", file, file.name)
    const uploadResponse = await fetch(`${aiServiceUrl}/v1/materials/upload`, {
      method: "POST",
      body: formData
    })

    if (!uploadResponse.ok) {
      return {
        ok: false,
        error: await responseError(uploadResponse)
      }
    }

    const uploadBody = await uploadResponse.json() as { material_id: string }
    const processResponse = await fetch(
      `${aiServiceUrl}/v1/materials/${uploadBody.material_id}/process`,
      { method: "POST" }
    )

    if (!processResponse.ok) {
      return {
        ok: false,
        modelMaterialId: uploadBody.material_id,
        error: await responseError(processResponse)
      }
    }

    const processBody = await processResponse.json() as {
      processing_status?: string
      total_pages?: number
      total_vision_requests?: number
      total_vision_responses?: number
      verified_count?: number
      needs_review_count?: number
      rejected_count?: number
    }

    const result: MaterialProcessingBridgeResult = {
      ok: processBody.processing_status !== "failed" && processBody.processing_status !== "rejected",
      modelMaterialId: uploadBody.material_id,
      processingStatus: processBody.processing_status,
      totalPages: processBody.total_pages,
      totalVisionRequests: processBody.total_vision_requests,
      totalVisionResponses: processBody.total_vision_responses,
      verifiedCount: processBody.verified_count,
      needsReviewCount: processBody.needs_review_count,
      rejectedCount: processBody.rejected_count
    }

    if (!scope || !result.ok) {
      return {
        ...result,
        activationStatus: scope ? "skipped" : undefined
      }
    }

    const activateResponse = await fetch(
      `${aiServiceUrl}/v1/materials/${uploadBody.material_id}/activate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          course_id: scope.courseId,
          class_session_id: scope.classSessionId
        })
      }
    )

    if (!activateResponse.ok) {
      return {
        ...result,
        ok: false,
        activationStatus: "failed",
        error: await responseError(activateResponse)
      }
    }

    const activateBody = await activateResponse.json() as {
      active_material_ids?: string[]
    }

    return {
      ...result,
      activationStatus: "activated",
      activeMaterialIds: activateBody.active_material_ids ?? []
    }
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "AI material processing failed"
    }
  }
}

export const activateModelMaterialWithModel = async (payload: {
  modelMaterialId: string
  courseId: string
  classSessionId: string
}) => {
  const aiServiceUrl = getAIServiceUrl()
  if (!aiServiceUrl) {
    return { ok: false, error: "AI_SERVICE_URL is not configured" }
  }

  try {
    const response = await fetch(`${aiServiceUrl}/v1/materials/${payload.modelMaterialId}/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        course_id: payload.courseId,
        class_session_id: payload.classSessionId
      })
    })

    if (!response.ok) {
      return { ok: false, error: await responseError(response) }
    }

    return { ok: true }
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "AI material activation failed"
    }
  }
}

const getAIServiceUrl = () => {
  const value = process.env.AI_SERVICE_URL?.trim()
  return value ? value.replace(/\/+$/, "") : null
}

const mapPhaseToModel = (phase: string) => {
  const normalized = phase.toLowerCase()
  if (normalized === "before") return "pre_class"
  if (normalized === "after") return "after_class"
  return "during_class"
}

const responseError = async (response: Response) => {
  const text = await response.text()
  try {
    const body = JSON.parse(text)
    if (typeof body?.detail === "string") return body.detail
    if (typeof body?.error === "string") return body.error
    return JSON.stringify(body)
  } catch {
    return text || `Request failed with status ${response.status}`
  }
}

const normalizeAIReferences = (
  references: RawAIReference[],
  provider: string,
  usedExternalAgent: boolean
): AIAnswerReference[] => {
  const normalized = references
    .map((reference) => {
      const materialId = reference.materialId ?? reference.material_id ?? null
      const rawSourceType = (reference.sourceType ?? reference.source_type ?? "").toUpperCase()
      const pageNumber = reference.pageNumber ?? reference.page_number ?? reference.page ?? null
      const sourceType: AIAnswerReference["sourceType"] =
        rawSourceType === "EXTERNAL_AI" || (!materialId && usedExternalAgent)
          ? "EXTERNAL_AI"
          : materialId
            ? "MATERIAL"
            : "EXTERNAL_AI"

      return {
        sourceType,
        materialId,
        materialFileName:
          reference.materialFileName ??
          reference.material_name ??
          reference.fileName ??
          reference.file_name ??
          null,
        pageNumber: typeof pageNumber === "number" && Number.isFinite(pageNumber) ? pageNumber : null,
        sourceQuote: reference.sourceQuote ?? reference.source_quote ?? reference.quote ?? null,
        sourceName: reference.sourceName ?? reference.source_name ?? null,
        provider: reference.provider ?? provider
      }
    })
    .filter((reference) =>
      reference.sourceType === "EXTERNAL_AI" ||
      Boolean(reference.materialId || reference.materialFileName || reference.sourceQuote)
    )

  const deduped = new Map<string, AIAnswerReference>()
  for (const reference of normalized) {
    const key = [
      reference.sourceType,
      reference.materialId ?? "",
      reference.materialFileName ?? "",
      reference.pageNumber ?? "",
      reference.sourceQuote ?? "",
      reference.provider ?? ""
    ].join("|")
    deduped.set(key, reference)
  }

  if (deduped.size === 0 && usedExternalAgent) {
    deduped.set("EXTERNAL_AI|||||", {
      sourceType: "EXTERNAL_AI",
      sourceName: "External AI answer",
      provider
    })
  }

  return [...deduped.values()]
}

export const callAIImageAnalysis = async (payload: {
  imageUrl: string
  sessionId: string
  availableMaterials: { id: string; fileName: string; fileUrl: string; fileType: string }[]
}) => {
  // Mock response while AI teammate isn't ready.
  return {
    materialId: null as string | null,
    pageNumber: null as number | null,
    confidence: 0,
    description: `Uploaded file received: ${payload.imageUrl}`
  }
}

export const callAIQuizGeneration = async (payload: {
  phase: string
  language: string
  criteria: { id: string; description: string; goal: string }[]
}) => {
  return payload.criteria.map((criterion, index) => ({
    criteriaId: criterion.id,
    questionText: `Explain how you would demonstrate this learning goal: ${criterion.description}`,
    questionType: "DIRECT" as const,
    options: null,
    correctConcept: criterion.goal,
    order: index + 1
  }))
}

export const callAIQuizScoring = async (payload: {
  questionText: string
  correctConcept: string
  studentAnswer: string
  language: string
}) => {
  const answer = payload.studentAnswer.trim()
  const normalize = (value: string) => value.toLowerCase().normalize("NFKC")
  const terms = (value: string) => [
    ...new Set(
      normalize(value)
        .match(/[a-z0-9]{4,}|[\u0e00-\u0e7f]{2,}/g)
        ?.filter((term) => !["using", "session", "material", "rubric", "goal", "evidence", "from"].includes(term)) ?? []
    )
  ]
  const keyTerms = terms(payload.correctConcept).slice(0, 24)
  const answerText = normalize(answer)
  const matchedTerms = keyTerms.filter((term) => answerText.includes(term)).length
  const coverage = keyTerms.length ? matchedTerms / keyTerms.length : 0
  const detailBonus = answer.length >= 120 ? 10 : answer.length >= 60 ? 5 : 0
  const score = Math.min(100, Math.round(45 + coverage * 45 + detailBonus))
  const isThai = payload.language === "th" || /[\u0e00-\u0e7f]/.test(answer)

  return {
    score,
    feedback: score >= 80
      ? isThai
        ? "คำตอบครอบคลุมแนวคิดหลักของ rubric และเชื่อมกับเนื้อหาใน session ได้ดี"
        : "Your answer covers the rubric goal and connects it to the session material."
      : score >= 50
        ? isThai
          ? "คำตอบแตะประเด็นสำคัญบางส่วนแล้ว แต่ควรเพิ่มคำอธิบายหรือคำสำคัญจากเนื้อหาให้ชัดขึ้น"
          : "Your answer addresses part of the rubric. Add clearer detail from the material."
        : isThai
          ? "คำตอบยังไม่สะท้อน rubric มากพอ ลองอธิบายแนวคิดหลักและยกตัวอย่างจากเนื้อหา"
          : "Your answer does not yet show enough evidence for the rubric. Explain the core idea and include an example.",
    evidence: `Matched ${matchedTerms}/${keyTerms.length} rubric terms. Student answer: ${answer}`
  }
}

const parseGeminiJson = (value: string) => {
  const trimmed = value.trim()
  const candidates = [trimmed]

  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i)?.[1]?.trim()
  if (fenced) {
    candidates.push(fenced)
  }

  const firstBrace = trimmed.indexOf("{")
  const lastBrace = trimmed.lastIndexOf("}")
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    candidates.push(trimmed.slice(firstBrace, lastBrace + 1))
  }

  const firstBracket = trimmed.indexOf("[")
  const lastBracket = trimmed.lastIndexOf("]")
  if (firstBracket >= 0 && lastBracket > firstBracket) {
    candidates.push(trimmed.slice(firstBracket, lastBracket + 1))
  }

  for (const candidate of candidates) {
    const normalized = candidate
      .replace(/^\s*json\s*/i, "")
      .replace(/,\s*([}\]])/g, "$1")
      .trim()

    try {
      const parsed = JSON.parse(normalized)
      return Array.isArray(parsed) ? parsed[0] : parsed
    } catch {
      // Try the next candidate extracted from the same Gemini response.
    }
  }

  throw new Error("Gemini did not return valid JSON")
}

export const callGeminiQuizScoring = async (payload: {
  questionText: string
  correctConcept: string
  studentAnswer: string
  language: string
  phase: "BEFORE" | "AFTER"
}) => {
  const apiKey = process.env.GEMINI_API_KEY?.trim()
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured")
  }

  const baseUrl = (
    process.env.GEMINI_API_BASE_URL?.trim() ||
    "https://generativelanguage.googleapis.com/v1beta"
  ).replace(/\/+$/, "")
  const model = (
    process.env.GEMINI_TEXT_MODEL?.trim() ||
    process.env.GEMINI_VISION_MODEL?.trim() ||
    "gemini-3.6-flash"
  )

  const prompt = [
    "You are grading a learning companion quiz answer.",
    "Grade only against the rubric, learning goal, and material evidence below.",
    "Do not reward confident but unsupported answers.",
    "Return strict JSON only with this shape:",
    '{"score": number, "feedback": string, "evidence": string}',
    "Score rubric:",
    "0-49 = not met, missing core ideas or unsupported.",
    "50-79 = partially met, correct but incomplete or weakly evidenced.",
    "80-100 = met, accurate, specific, and supported by the material/rubric.",
    "Use 0 only for blank answers, 'I don't know', refusals, or answers that are completely unrelated.",
    "Give 10-49 for answers that mention a relevant course keyword but do not explain, support, or apply it.",
    payload.phase === "AFTER"
      ? "This is a post-class quiz. Require application, correction of misunderstandings, and clear evidence that the student now meets the criterion."
      : "This is a pre-class quiz. Measure readiness and identify gaps before class.",
    payload.language === "th"
      ? "Write feedback in clear Thai. Keep technical terms such as AWS, EC2, IAM in English."
      : "Write feedback in clear English.",
    "",
    `Question: ${payload.questionText}`,
    `Rubric and expected concept:\n${payload.correctConcept}`,
    `Student answer:\n${payload.studentAnswer}`,
  ].join("\n")

  const response = await fetch(`${baseUrl}/models/${model}:generateContent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": apiKey,
    },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0,
        maxOutputTokens: 1024,
        responseMimeType: "application/json",
      },
    }),
  })

  const text = await response.text()
  if (!response.ok) {
    throw new Error(text || `Gemini quiz scoring failed with status ${response.status}`)
  }

  const body = JSON.parse(text) as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>
  }
  const candidateText = body.candidates?.[0]?.content?.parts
    ?.map((part) => part.text ?? "")
    .join("")
    .trim()

  if (!candidateText) {
    throw new Error("Gemini returned an empty quiz score")
  }

  let parsed: {
    score?: unknown
    feedback?: unknown
    evidence?: unknown
  }

  try {
    parsed = parseGeminiJson(candidateText) as {
      score?: unknown
      feedback?: unknown
      evidence?: unknown
    }
  } catch (error) {
    console.warn("Gemini quiz score JSON parse failed; using local fallback.", {
      error,
      preview: candidateText.slice(0, 300),
    })
    const fallback = await callAIQuizScoring({
      questionText: payload.questionText,
      correctConcept: payload.correctConcept,
      studentAnswer: payload.studentAnswer,
      language: payload.language,
    })

    return {
      score: fallback.score,
      feedback: fallback.feedback,
      evidence: `Fallback local scoring used because Gemini returned invalid JSON. ${fallback.evidence}`,
    }
  }
  const score = typeof parsed.score === "number"
    ? Math.max(0, Math.min(100, parsed.score))
    : 0

  return {
    score,
    feedback: typeof parsed.feedback === "string"
      ? parsed.feedback
      : "The answer was scored, but Gemini did not return feedback.",
    evidence: typeof parsed.evidence === "string"
      ? parsed.evidence
      : `Gemini score: ${score}`,
  }
}

export const callAIInsight = async (payload: {
  criteriaResults: unknown[]
  duringClassLogs: unknown[]
  caughtUpCount: number
  totalStudents: number
}) => {
  void payload
  // Mock response while AI teammate isn't ready.
  return { insight: "Mock insight for testing" }
}

export const callAIWeeklySummary = async (payload: {
  subjectName: string
  weekNumber: number
  avgReadiness: number
  semesterProgress: number
}) => {
  return {
    summary: `Mock weekly summary for ${payload.subjectName}, week ${payload.weekNumber}: average readiness is ${payload.avgReadiness.toFixed(1)}%.`
  }
}

