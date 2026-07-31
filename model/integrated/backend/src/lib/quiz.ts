import { callAIChat, callAIQuizScoring, callGeminiQuizScoring } from "@/lib/ai"
import { activateProcessedSessionMaterials, type ActiveSession } from "@/lib/chat"

export type GeneratedQuizQuestion = {
  criteriaId: string
  questionText: string
  questionType: "DIRECT" | "SCENARIO" | "REASONING"
  options: null
  correctConcept: string
  order: number
  sourceExcerpt: string
  rubricDescription: string
  rubricGoal: string
}

export type QuizPhase = "BEFORE" | "AFTER"

export type PersonalizationContext = {
  weakCriteriaIds: string[]
  recentStudentQuestions: string[]
  previousFeedback: string[]
}

const readQuizQuestionLimit = () => {
  const parsed = Number.parseInt(process.env.QUIZ_MAX_QUESTIONS_PER_ATTEMPT ?? "3", 10)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 3
  }
  return Math.min(parsed, 10)
}

const cleanEvidence = (value: string) =>
  value
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^Based on the uploaded material:\s*/i, "")
    .replace(/^From the uploaded material, this session is about:\s*/i, "")
    .trim()
    .slice(0, 900)

const makeReadableFocus = (description: string, sessionTitle: string) => {
  const cleaned = description
    .replace(/^explain\s+/i, "")
    .replace(/^apply\s+/i, "")
    .replace(/\.$/, "")
    .trim()

  if (!cleaned || /key ideas? from/i.test(cleaned)) {
    return `the main concept from ${sessionTitle}`
  }

  return cleaned
}

const answerRequirements = (phase: QuizPhase) => [
  "Strong answer requirements:",
  "- State the main concept in your own words.",
  "- Include at least one concrete detail from the material evidence.",
  phase === "AFTER"
    ? "- Apply the concept to a realistic case, decision, or example."
    : "- Explain why the detail matters for class readiness.",
  "- Avoid one-line topic labels without explanation.",
].join("\n")

export const generateQuizFromKbAndRubric = async ({
  session,
  studentId,
  language,
  phase,
  personalization
}: {
  session: ActiveSession
  studentId: string
  language: string
  phase: QuizPhase
  personalization?: PersonalizationContext
}): Promise<GeneratedQuizQuestion[]> => {
  await activateProcessedSessionMaterials(session)

  const orderedCriteria = [
    ...session.sessionCriteria.filter((criterion) =>
      phase === "AFTER" && personalization?.weakCriteriaIds.includes(criterion.id)
    ),
    ...session.sessionCriteria.filter((criterion) =>
      phase !== "AFTER" || !personalization?.weakCriteriaIds.includes(criterion.id)
    ),
  ].slice(0, readQuizQuestionLimit())
  const recentQuestions = personalization?.recentStudentQuestions.slice(0, 5) ?? []
  const previousFeedback = personalization?.previousFeedback.slice(0, 5) ?? []

  const questions = await Promise.all(
    orderedCriteria.map(async (criterion, index) => {
      let evidence = ""
      try {
        const result = await callAIChat({
          phase: phase.toLowerCase(),
          language,
          studentId,
          sessionId: session.id,
          courseId: session.subjectId,
          classSessionId: session.id,
          studentMessage: [
            "Find only the uploaded material evidence needed for this rubric.",
            `Rubric: ${criterion.description}`,
            `Learning goal: ${criterion.goal}`,
            phase === "AFTER"
              ? [
                  "This evidence will be used for a post-class quiz targeted to one student.",
                  recentQuestions.length ? `Student asked: ${recentQuestions.join(" | ")}` : "",
                  previousFeedback.length ? `Previous quiz feedback: ${previousFeedback.join(" | ")}` : "",
                ].filter(Boolean).join("\n")
              : ""
          ].join("\n"),
          recentMessages: [],
          summary: "",
          sessionCriteria: [{ id: criterion.id, description: criterion.description, goal: criterion.goal }],
          teacherMaterial: session.materials.map((material) => material.fileName).join(", ")
        })
        evidence = cleanEvidence(result.response)
      } catch (error) {
        console.warn(`Could not fetch KB evidence for criterion ${criterion.id}:`, error)
      }

      const fallbackEvidence = [
        criterion.goal,
        criterion.description,
        session.materials.map((material) => material.fileName).join(", ")
      ].filter(Boolean).join(" ")

      const sourceExcerpt = evidence || fallbackEvidence
      const questionType: GeneratedQuizQuestion["questionType"] =
        phase === "AFTER"
          ? index % 2 === 0 ? "SCENARIO" : "REASONING"
          : index % 3 === 1 ? "SCENARIO" : index % 3 === 2 ? "REASONING" : "DIRECT"
      const personalizationHint = phase === "AFTER" && (recentQuestions.length || previousFeedback.length)
        ? [
            recentQuestions.length ? `Use this student's earlier questions as context: ${recentQuestions.join(" | ")}` : "",
            previousFeedback.length ? `Address these earlier gaps: ${previousFeedback.join(" | ")}` : "",
          ].filter(Boolean).join(" ")
        : ""
      const focus = makeReadableFocus(criterion.description, session.title)

      return {
        criteriaId: criterion.id,
        questionText:
          phase === "AFTER"
            ? questionType === "SCENARIO"
              ? `Post-class check: Apply ${focus} to a realistic case. Include one material detail and explain the connection.`
              : `Post-class check: Explain ${focus} in your own words, then show how your understanding changed or became clearer.`
            : questionType === "SCENARIO"
              ? `Apply ${focus} to a practical example. Include one detail from the uploaded material.`
              : questionType === "REASONING"
                ? `Explain why ${focus} matters for this session. Use evidence from the material.`
                : `Using the session material, explain ${focus}. Include one specific example or detail.`,
        questionType,
        options: null,
        correctConcept: [
          `Quiz phase: ${phase}`,
          `Rubric: ${criterion.description}`,
          `Goal: ${criterion.goal}`,
          personalizationHint ? `Student-specific context: ${personalizationHint}` : "",
          `Material evidence used for this question: ${sourceExcerpt}`,
          answerRequirements(phase),
          phase === "AFTER"
            ? "Passing requires accurate application, not just repeating keywords."
            : ""
        ].filter(Boolean).join("\n"),
        order: index + 1,
        sourceExcerpt,
        rubricDescription: criterion.description,
        rubricGoal: criterion.goal
      }
    })
  )

  return questions
}

export const scoreQuizAnswer = async ({
  questionText,
  correctConcept,
  studentAnswer,
  language,
  phase
}: {
  questionText: string
  correctConcept: string
  studentAnswer: string
  language: string
  phase: QuizPhase
}) => {
  if (phase === "AFTER") {
    try {
      return await callGeminiQuizScoring({
        questionText,
        correctConcept,
        studentAnswer,
        language,
        phase,
      })
    } catch (error) {
      console.warn("Gemini quiz scoring failed; using local fallback.", error)
      const fallback = await callAIQuizScoring({
        questionText,
        correctConcept,
        studentAnswer,
        language
      })

      return {
        ...fallback,
        evidence: `Fallback local scoring used because Gemini scoring failed. ${fallback.evidence}`
      }
    }
  }

  return callAIQuizScoring({
    questionText,
    correctConcept,
    studentAnswer,
    language
  })
}
