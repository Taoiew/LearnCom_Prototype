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

const cleanEvidence = (value: string) =>
  value
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^Based on the uploaded material:\s*/i, "")
    .replace(/^From the uploaded material, this session is about:\s*/i, "")
    .trim()
    .slice(0, 900)

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
  ]
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

      return {
        criteriaId: criterion.id,
        questionText:
          phase === "AFTER"
            ? questionType === "SCENARIO"
              ? `Post-class check: apply ${criterion.description} to a realistic case from this session.`
              : `Post-class check: explain how you corrected or confirmed your understanding of ${criterion.goal}.`
            : questionType === "SCENARIO"
              ? `Apply this session material to a practical example: ${criterion.description}`
              : questionType === "REASONING"
                ? `Explain the reasoning behind this rubric goal: ${criterion.goal}`
                : `Using the session material, explain: ${criterion.description}`,
        questionType,
        options: null,
        correctConcept: [
          `Quiz phase: ${phase}`,
          `Rubric: ${criterion.description}`,
          `Goal: ${criterion.goal}`,
          personalizationHint ? `Student-specific context: ${personalizationHint}` : "",
          `Material evidence used for this question: ${sourceExcerpt}`,
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
    return callGeminiQuizScoring({
      questionText,
      correctConcept,
      studentAnswer,
      language,
      phase,
    })
  }

  return callAIQuizScoring({
    questionText,
    correctConcept,
    studentAnswer,
    language
  })
}
