"use client";

import React, { useEffect, useState } from "react";
import {
  UploadCloud,
  FileText,
  Upload,
  File,
  X,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import {
  getTeacherDashboardViewModel,
  uploadMaterialsForSession,
  type TeacherSession,
} from "@/lib/api";
import TeacherSidebar from "@/components/teachersidebar";

export default function MaterialsAndPromptsPage() {
  const [activeTab, setActiveTab] = useState<
    "materials" | "rubrics" | "prompts"
  >("materials");

  const [materialsFiles, setMaterialsFiles] = useState<File[]>([]);
  const [rubricsFiles, setRubricsFiles] = useState<File[]>([]);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [sessions, setSessions] = useState<TeacherSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let ignore = false;

    getTeacherDashboardViewModel()
      .then((viewModel) => {
        if (ignore) return;
        const allSessions = Object.values(viewModel.sessionsBySubject).flat();
        setSessions(allSessions);
        setSelectedSessionId(allSessions[0]?.id ?? "");
      })
      .catch((error) => {
        if (!ignore) {
          setLoadError(
            error instanceof Error ? error.message : "Failed to load sessions.",
          );
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const [promptText, setPromptText] = useState(
    "Answer in a Socratic style: ask one clarifying question before giving a full answer, and always tie explanations back to a real AWS scenario. Keep tone encouraging, never dismissive of a wrong guess.",
  );
  const [questionTypes, setQuestionTypes] = useState<{
    [key: string]: boolean;
  }>({
    multipleChoice: true,
    writtenShort: true,
    trueFalse: false,
  });
  const [numQuestions, setNumQuestions] = useState<number>(5);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      if (activeTab === "materials") {
        setMaterialsFiles((prev) => [...prev, ...selectedFiles]);
      } else if (activeTab === "rubrics") {
        setRubricsFiles((prev) => [...prev, ...selectedFiles]);
      }
      setUploadSuccess(false);
    }
  };

  const handleRemoveFile = (index: number) => {
    if (activeTab === "materials") {
      setMaterialsFiles((prev) => prev.filter((_, i) => i !== index));
    } else {
      setRubricsFiles((prev) => prev.filter((_, i) => i !== index));
    }
    setUploadSuccess(false);
  };

  const handleUploadSubmit = async () => {
    const filesToUpload =
      activeTab === "materials" ? materialsFiles : rubricsFiles;
    if (filesToUpload.length === 0) return;

    setIsUploading(true);
    setUploadSuccess(false);

    try {
      if (activeTab === "materials") {
        await uploadMaterialsForSession(filesToUpload, selectedSessionId);
      } else {
        await uploadMaterialsForSession(filesToUpload, selectedSessionId);
      }

      setUploadSuccess(true);
    } catch (error) {
      console.error("Upload failed:", error);
      alert(error instanceof Error ? error.message : "Failed to upload files.");
    } finally {
      setIsUploading(false);
    }
  };

  const toggleQuestionType = (type: string) => {
    setQuestionTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  const currentFiles =
    activeTab === "materials" ? materialsFiles : rubricsFiles;
  const [isSavedModalOpen, setIsSavedModalOpen] = useState(false);

  const handleSaveForSession = (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    setIsSavedModalOpen(true);

    setTimeout(() => {
      setIsSavedModalOpen(false);
    }, 1000);
  };

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <TeacherSidebar />

      <main
        className="flex-1 pl-64 px-8 pt-14 pb-20 relative overflow-y-auto min-h-screen"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 w-full max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div>
            <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
              Materials & prompts
            </h2>
            <p className="text-xs text-stone-500 mt-1">
              Everything the companion needs to prep students for this subject.
            </p>
          </div>

          {loadError && (
            <div className="bg-white border border-red-100 rounded-xl p-4 text-sm text-red-500">
              {loadError}
            </div>
          )}

          <div className="bg-white border border-stone-200/70 rounded-xl p-4">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-stone-400 mb-2">
              Target session
            </label>
            <select
              value={selectedSessionId}
              onChange={(event) => setSelectedSessionId(event.target.value)}
              className="w-full h-10 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-800 outline-none focus:border-orange-400"
            >
              {sessions.length === 0 ? (
                <option value="">No real sessions available</option>
              ) : (
                sessions.map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.week} - {session.title}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Navigation Segmented Tabs */}
          <div className="bg-white/60 backdrop-blur-sm p-1 rounded-2xl border border-stone-200/60 grid grid-cols-3 gap-1 w-full">
            <button
              type="button"
              onClick={() => setActiveTab("materials")}
              className={`py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                activeTab === "materials"
                  ? "bg-[#e65100] text-white shadow-sm"
                  : "text-stone-600 hover:text-stone-900 hover:bg-white/50"
              }`}
            >
              Materials
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("rubrics")}
              className={`py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                activeTab === "rubrics"
                  ? "bg-[#e65100] text-white shadow-sm"
                  : "text-stone-600 hover:text-stone-900 hover:bg-white/50"
              }`}
            >
              Rubrics
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("prompts")}
              className={`py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                activeTab === "prompts"
                  ? "bg-[#e65100] text-white shadow-sm"
                  : "text-stone-600 hover:text-stone-900 hover:bg-white/50"
              }`}
            >
              System prompts
            </button>
          </div>

          {/* TAB 1 & 2: MATERIALS / RUBRICS */}
          {(activeTab === "materials" || activeTab === "rubrics") && (
            <div className="space-y-6 w-full">
              {/* Drag and Drop Zone */}
              <div className="bg-white border-2 border-dashed border-stone-200 rounded-2xl p-7 text-center flex flex-col items-center justify-center space-y-3">
                <div className="w-11 h-13 rounded-full bg-orange-50 flex items-center justify-center text-[#e65100]">
                  <UploadCloud size={22} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-stone-900">
                    Drag and drop files here
                  </h3>
                  <p className="text-xs text-stone-400 mt-0.5">
                    {activeTab === "materials"
                      ? "or browse from your device - PDF, DOCX, PPTX up to 25 MB"
                      : "grading rubrics or scoring guides - PDF, DOCX, XLSX up to 25 MB"}
                  </p>
                </div>

                <label className="mt-1 bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold text-xs px-4 py-2 rounded-xl border border-stone-300 transition-all active:scale-95 flex items-center gap-2 cursor-pointer">
                  <Upload size={14} />
                  <span>Browse files</span>
                  <input
                    type="file"
                    onChange={handleFileChange}
                    multiple
                    className="hidden"
                    accept={
                      activeTab === "materials"
                        ? ".pdf,.docx,.pptx"
                        : ".pdf,.docx,.xlsx"
                    }
                  />
                </label>
              </div>

              {/* Recently / Selected Uploaded Section */}
              <div className="space-y-3 pt-1">
                <h4 className="text-xs font-bold text-stone-500">
                  {currentFiles.length > 0
                    ? "Selected files ready to publish"
                    : "Recently uploaded"}
                </h4>

                {currentFiles.length === 0 ? (
                  <div className="bg-white/40 border border-dashed border-stone-200/80 rounded-2xl p-10 text-center flex flex-col items-center justify-center space-y-2">
                    <div className="w-10 h-10 rounded-full bg-stone-100 flex items-center justify-center text-stone-400">
                      <FileText size={18} />
                    </div>
                    <p className="text-xs font-bold text-stone-800">
                      {activeTab === "materials"
                        ? "No materials uploaded yet"
                        : "No rubrics uploaded yet"}
                    </p>
                    <p className="text-[11px] text-stone-400 max-w-xs">
                      Files you add above will appear here before you publish
                      them to students.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {currentFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="bg-white border border-stone-200/80 rounded-xl p-3.5 flex items-center justify-between shadow-sm"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-orange-50 text-[#e65100] flex items-center justify-center">
                            <File size={16} />
                          </div>
                          <div>
                            <p className="text-xs font-bold text-stone-800">
                              {file.name}
                            </p>
                            <p className="text-[10px] text-stone-400">
                              {(file.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(idx)}
                          disabled={isUploading}
                          className="text-stone-400 hover:text-red-500 p-1.5 transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {currentFiles.length > 0 && (
                <div className="flex items-center justify-between pt-2">
                  {uploadSuccess && (
                    <div className="flex items-center gap-1.5 text-emerald-600 text-xs font-bold">
                      <CheckCircle2 size={16} />
                      <span>Uploaded and published successfully!</span>
                    </div>
                  )}

                  <div className="ml-auto">
                    <button
                      type="button"
                      onClick={handleUploadSubmit}
                      disabled={isUploading}
                      className="bg-[#e65100] hover:bg-[#d84315] text-white font-bold text-xs px-8 py-3 rounded-xl shadow-md transition-all active:scale-95 flex items-center gap-2 cursor-pointer disabled:opacity-50"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 size={16} className="animate-spin" />
                          <span>Uploading files...</span>
                        </>
                      ) : (
                        <>
                          <Upload size={16} />
                          <span>
                            Publish{" "}
                            {activeTab === "materials"
                              ? "materials"
                              : "rubrics"}{" "}
                            ({currentFiles.length})
                          </span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: SYSTEM PROMPTS */}
          {activeTab === "prompts" && (
            <div className="space-y-4 w-full">
              {/* Card 1 */}
              <div className="bg-white border border-stone-200/60 rounded-2xl p-8 shadow-sm space-y-3">
                <div>
                  <h3 className="text-sm font-bold text-stone-900">
                    How should the companion respond?
                  </h3>
                  <p className="text-xs text-stone-400 mt-1 leading-relaxed">
                    This briefs the AI on tone, teaching style, and how strictly
                    to guide students toward the answer during pre-class chat.
                  </p>
                </div>
                <textarea
                  rows={3}
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 rounded-xl p-3 text-xs text-stone-800 outline-none focus:border-orange-500 focus:bg-white transition-all leading-relaxed resize-y font-medium"
                />
              </div>

              {/* Card 2 */}
              <div className="bg-white border border-stone-200/60 rounded-2xl p-5 shadow-sm space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-stone-900">
                    Readiness quiz format
                  </h3>
                  <p className="text-xs text-stone-400 mt-1">
                    Choose which question types the quiz should draw from for
                    this session.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => toggleQuestionType("multipleChoice")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                      questionTypes.multipleChoice
                        ? "bg-orange-50 border-orange-200 text-[#e65100]"
                        : "bg-stone-50 border-stone-200 text-stone-600 hover:bg-stone-100"
                    }`}
                  >
                    Multiple choice
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleQuestionType("writtenShort")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                      questionTypes.writtenShort
                        ? "bg-orange-50 border-orange-200 text-[#e65100]"
                        : "bg-stone-50 border-stone-200 text-stone-600 hover:bg-stone-100"
                    }`}
                  >
                    Written / short answer
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleQuestionType("trueFalse")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                      questionTypes.trueFalse
                        ? "bg-orange-50 border-orange-200 text-[#e65100]"
                        : "bg-stone-50 border-stone-200 text-stone-600 hover:bg-stone-100"
                    }`}
                  >
                    True / false
                  </button>
                </div>

                <div className="space-y-1.5 pt-1">
                  <label className="text-xs font-bold text-stone-800 block">
                    Number of questions
                  </label>
                  <input
                    type="number"
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    min={1}
                    max={20}
                    className="w-28 bg-stone-50 border border-stone-200 rounded-xl px-3 py-1.5 text-xs font-bold text-stone-900 outline-none focus:border-orange-500 focus:bg-white transition-all"
                  />
                </div>
              </div>

              {/* Save Button */}
              <div className="flex justify-end pt-1">
                <button
                  type="button"
                  onClick={handleSaveForSession}
                  className="bg-[#e65100] hover:bg-[#d84315] text-white font-bold px-6 py-3 rounded-full text-xs shadow-sm transition-all active:scale-95 cursor-pointer"
                >
                  Save for this session
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {isSavedModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-[2px] transition-all animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl p-8 shadow-2xl border border-stone-100 flex flex-col items-center text-center max-w-sm w-full mx-4 space-y-3 transform animate-in zoom-in-95 duration-200">
            <div className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-500 flex items-center justify-center">
              <CheckCircle2 size={32} strokeWidth={2.5} />
            </div>

            <div>
              <h3 className="text-lg font-bold text-stone-900">Saved</h3>
              <p className="text-xs text-stone-500 mt-1">
                Prompt and quiz settings updated for this session.
              </p>
            </div>
          </div>
        </div>
      )}
    </div> 
  );
}
