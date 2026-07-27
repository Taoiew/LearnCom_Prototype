"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, ChevronLeft, Loader2 } from "lucide-react";
import StudentSidebar from "@/components/studentsidebar";
import {
  generateReadinessQuiz,
  getSessionDetails,
  submitReadinessQuiz,
  type ApiSessionResponse,
  type GeneratedReadinessQuiz,
  type QuizPhase,
  type SubmittedQuizResult,
} from "@/lib/api";

export default function ReadinessQuizPage() {
  const params = useParams();
  const sessionId = String(params?.id ?? "");
  const [session, setSession] = useState<ApiSessionResponse | null>(null);
  const [loadError, setLoadError] = useState("");
  const [quiz, setQuiz] = useState<GeneratedReadinessQuiz | null>(null);
  const [selectedPhase, setSelectedPhase] = useState<QuizPhase>("BEFORE");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SubmittedQuizResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [quizError, setQuizError] = useState("");

  useEffect(() => {
    let ignore = false;

    getSessionDetails(sessionId)
      .then((nextSession) => {
        if (!ignore) setSession(nextSession);
      })
      .catch((error) => {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load session.",
          );
        }
      });

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  const handleGenerateQuiz = async () => {
    if (!session || isGenerating) return;
    setQuizError("");
    setResult(null);
    setIsGenerating(true);
    try {
      const nextQuiz = await generateReadinessQuiz({
        sessionId,
        phase: selectedPhase,
      });
      setQuiz(nextQuiz);
      setAnswers({});
    } catch (error) {
      setQuizError(
        error instanceof Error ? error.message : "Failed to generate quiz.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quiz || isSubmitting) return;
    const nextAnswers = quiz.questions.map((question) => ({
      questionId: question.id,
      answer: answers[question.id]?.trim() ?? "",
    }));

    if (nextAnswers.some((answer) => !answer.answer)) {
      setQuizError("Please answer every question before submitting.");
      return;
    }

    setQuizError("");
    setIsSubmitting(true);
    try {
      setResult(
        await submitReadinessQuiz({
          quizId: quiz.quizId,
          answers: nextAnswers,
        }),
      );
    } catch (error) {
      setQuizError(
        error instanceof Error ? error.message : "Failed to submit quiz.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const readinessLabel =
    result?.readiness === "READY"
      ? "Ready"
      : result?.readiness === "PARTIAL"
        ? "Partially ready"
        : result
          ? "Needs review"
          : "";

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <StudentSidebar />
      <main
        className="flex-1 pl-64 px-8 pt-12 pb-8 relative overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 mx-auto w-full max-w-6xl space-y-5">
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-1 text-xs font-semibold text-stone-500 hover:text-stone-800 mb-3 transition-colors cursor-pointer"
          >
            <ChevronLeft size={16} /> Back to session
          </button>

          <div>
            <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
              {selectedPhase === "BEFORE" ? "Pre-class readiness quiz" : "Post-class mastery quiz"}
            </h2>
            <p className="text-xs text-stone-400 mt-1">
              {session?.title ?? loadError ?? "Loading real session..."}
            </p>
          </div>

          <div className="min-h-[520px] bg-white border border-stone-200/80 rounded-2xl p-8 shadow-sm text-sm text-stone-500">
            {!quiz && (
              <div className="space-y-6">
                <div className="inline-grid grid-cols-2 rounded-full bg-stone-100 p-1 text-xs font-bold text-stone-500">
                  {(["BEFORE", "AFTER"] as QuizPhase[]).map((phase) => (
                    <button
                      key={phase}
                      type="button"
                      onClick={() => {
                        setSelectedPhase(phase);
                        setQuizError("");
                      }}
                      className={[
                        "rounded-full px-5 py-2 transition-all",
                        selectedPhase === phase
                          ? "bg-white text-[#d84315] shadow-sm"
                          : "hover:text-stone-800",
                      ].join(" ")}
                    >
                      {phase === "BEFORE" ? "Before class" : "After class"}
                    </button>
                  ))}
                </div>

                <div className="flex flex-col gap-5 rounded-2xl bg-stone-50/60 p-6 md:flex-row md:items-center md:justify-between">
                  <div className="space-y-2">
                    <h3 className="text-lg font-bold text-stone-900">
                      {selectedPhase === "BEFORE"
                        ? "Generate a pre-class readiness check"
                        : "Generate a personalized post-class check"}
                    </h3>
                    <p className="max-w-3xl text-sm leading-relaxed text-stone-500">
                      {selectedPhase === "BEFORE"
                        ? "This quiz uses session materials and rubric criteria to measure whether you are ready before class."
                        : "This quiz uses the session rubric, material evidence, your earlier chat questions, and earlier quiz gaps. Answers are graded more strictly with Gemini."}
                    </p>
                    {quizError && (
                      <p className="text-xs font-semibold text-red-500">
                        {quizError}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={handleGenerateQuiz}
                    disabled={!session || isGenerating}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-[#e65100] px-6 py-3 text-xs font-bold text-white shadow-sm transition-all hover:bg-[#d84315] disabled:opacity-50 md:min-w-[190px]"
                  >
                    {isGenerating && <Loader2 size={15} className="animate-spin" />}
                    {selectedPhase === "BEFORE" ? "Generate pre-quiz" : "Generate post-quiz"}
                  </button>
                </div>
              </div>
            )}

            {quiz && (
              <div className="space-y-6">
                <div className="flex flex-col gap-3 border-b border-stone-100 pb-5 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3 className="text-base font-bold text-stone-900">
                      {quiz.questions.length} {quiz.phase === "AFTER" ? "personalized post-class" : "pre-class"} questions
                    </h3>
                    <p className="text-xs text-stone-400">
                      {quiz.phase === "AFTER"
                        ? "Use your own words and apply the idea. Gemini grading checks whether the rubric is truly met."
                        : "Answer in your own words. Short but specific is enough."}
                    </p>
                  </div>
                  {result && (
                    <div className="rounded-2xl bg-orange-50 px-4 py-3 text-right">
                      <p className="text-xs font-bold uppercase tracking-wide text-[#d84315]">
                        {readinessLabel}
                      </p>
                      <p className="text-2xl font-bold text-stone-900">
                        {Math.round(result.totalScore)}%
                      </p>
                    </div>
                  )}
                </div>

                {quiz.questions.map((question) => {
                  const criteriaResult = result?.criteriaResults.find(
                    (item) => item.criteriaId === question.criteriaId,
                  );

                  return (
                    <div
                      key={question.id}
                      className="space-y-4 rounded-2xl border border-stone-200/70 bg-stone-50/60 p-5"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2">
                          <p className="text-xs font-bold uppercase tracking-wide text-[#d84315]">
                            Question {question.order} - {question.questionType.toLowerCase()}
                          </p>
                          <h4 className="text-base font-bold leading-snug text-stone-900">
                            {question.questionText}
                          </h4>
                        </div>
                        {criteriaResult && (
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-stone-700 ring-1 ring-stone-200">
                            {criteriaResult.status.replace("_", " ")}
                          </span>
                        )}
                      </div>

                      <div className="grid gap-3 lg:grid-cols-2">
                        <div className="rounded-xl bg-white p-4 ring-1 ring-stone-200">
                          <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                            Rubric
                          </p>
                          <p className="mt-2 text-xs font-semibold leading-relaxed text-stone-700">
                            {question.rubric.description}
                          </p>
                          <p className="mt-2 text-xs leading-relaxed text-stone-500">
                            Goal: {question.rubric.goal}
                          </p>
                        </div>
                        <div className="rounded-xl bg-white p-4 ring-1 ring-stone-200">
                          <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                            Material evidence used for this question
                          </p>
                          <p className="mt-2 line-clamp-4 text-xs leading-relaxed text-stone-500">
                            {question.sourceExcerpt || "No readable material evidence was available."}
                          </p>
                        </div>
                      </div>

                      <textarea
                        value={answers[question.id] ?? ""}
                        onChange={(event) =>
                          setAnswers((current) => ({
                            ...current,
                            [question.id]: event.target.value,
                          }))
                        }
                        disabled={Boolean(result)}
                        rows={5}
                        placeholder="Write your answer here..."
                        className="w-full resize-y rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-900 outline-none transition-all focus:border-orange-500 disabled:bg-stone-100"
                      />

                      {criteriaResult && (
                        <div className="flex items-start gap-2 rounded-xl bg-white p-4 text-xs leading-relaxed text-stone-600 ring-1 ring-stone-200">
                          <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0 text-[#e65100]" />
                          <p>{criteriaResult.feedback}</p>
                        </div>
                      )}
                    </div>
                  );
                })}

                {quizError && (
                  <p className="text-xs font-semibold text-red-500">
                    {quizError}
                  </p>
                )}

                <div className="flex justify-end gap-3">
                  {!result && (
                    <button
                      type="button"
                      onClick={handleSubmitQuiz}
                      disabled={isSubmitting}
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-[#e65100] px-7 py-3 text-xs font-bold text-white shadow-sm transition-all hover:bg-[#d84315] disabled:opacity-50"
                    >
                      {isSubmitting && <Loader2 size={15} className="animate-spin" />}
                      Submit quiz
                    </button>
                  )}
                  {result && (
                    <p className="text-sm font-semibold text-stone-700">
                      {result.recommendation}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
