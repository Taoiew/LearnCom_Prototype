"use client";

import React, { useState } from "react";
import { Plus, Trash2, CheckCircle2 } from "lucide-react";
import TeacherSidebar from "@/components/teachersidebar";

export default function SubjectSettingsPage() {
  const [subjectName, setSubjectName] = useState("");
  const [subjectCode, setSubjectCode] = useState("");
  const [semesterStart, setSemesterStart] = useState("");
  const [semesterEnd, setSemesterEnd] = useState("");

  const [criteria, setCriteria] = useState<string[]>([]);

  const handleCriterionChange = (index: number, value: string) => {
    const updated = [...criteria];
    updated[index] = value;
    setCriteria(updated);
  };

  const handleAddCriterion = () => {
    setCriteria([...criteria, ""]);
  };

  const handleRemoveCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const [isSavedModalOpen, setIsSavedModalOpen] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();

    setIsSavedModalOpen(true);

    setTimeout(() => {
      setIsSavedModalOpen(false);
    }, 1000);
  };

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <TeacherSidebar />

      <main
        className="flex-1 pl-64 px-8 pt-14 pb-8 relative overflow-y-auto h-screen
        [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div>
            <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
              Subject settings
            </h2>
            <p className="text-xs text-stone-500 mt-1">
              Manage the basic details and criteria for this subject.
            </p>
          </div>

          {/* Form Card */}
          <form onSubmit={handleSave} className="space-y-6">
            <div className="bg-white border border-stone-200/60 rounded-3xl p-8 shadow-sm space-y-6">
              {/* Row 1: Subject Name & Subject Code */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2 space-y-1.5">
                  <label className="text-xs font-bold text-stone-700 block">
                    Subject name
                  </label>
                  <input
                    type="text"
                    value={subjectName}
                    onChange={(e) => setSubjectName(e.target.value)}
                    className="w-full bg-stone-200/50 border border-transparent rounded-xl px-4 py-2.5 text-xs font-medium text-stone-900 outline-none focus:border-orange-500 focus:bg-white transition-all"
                    placeholder="e.g. Basic Cloud Computing"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-stone-700 block">
                    Subject code
                  </label>
                  <input
                    type="text"
                    value={subjectCode}
                    onChange={(e) => setSubjectCode(e.target.value)}
                    className="w-full bg-stone-200/50 border border-transparent rounded-xl px-4 py-2.5 text-xs font-medium text-stone-900 outline-none focus:border-orange-500 focus:bg-white transition-all"
                    placeholder="e.g. COURSE101"
                  />
                </div>
              </div>

              {/* Row 2: Semester Start & Semester End */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-stone-700 block">
                    Semester start
                  </label>
                  <input
                    type="date"
                    value={semesterStart}
                    onChange={(e) => setSemesterStart(e.target.value)}
                    className="w-full bg-stone-200/50 border border-transparent rounded-xl px-4 py-2.5 text-xs font-medium text-stone-900 outline-none focus:border-orange-500 focus:bg-white transition-all cursor-pointer"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-stone-700 block">
                    Semester end
                  </label>
                  <input
                    type="date"
                    value={semesterEnd}
                    onChange={(e) => setSemesterEnd(e.target.value)}
                    className="w-full bg-stone-200/50 border border-transparent rounded-xl px-4 py-2.5 text-xs font-medium text-stone-900 outline-none focus:border-orange-500 focus:bg-white transition-all cursor-pointer"
                  />
                </div>
              </div>

              {/* Section 3: Subject Criteria Dynamic List */}
              <div className="space-y-3 pt-2">
                <label className="text-xs font-bold text-stone-700 block">
                  Subject criteria ({criteria.length})
                </label>

                <div className="space-y-2.5">
                  {criteria.map((item, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={item}
                        onChange={(e) =>
                          handleCriterionChange(index, e.target.value)
                        }
                        placeholder={`Criterion #${index + 1}`}
                        className="flex-1 bg-stone-200/50 border border-transparent rounded-xl px-4 py-2.5 text-xs font-medium text-stone-900 outline-none focus:border-orange-500 focus:bg-white transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveCriterion(index)}
                        className="p-2.5 text-stone-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all cursor-pointer border border-stone-200/60"
                        title="Delete criterion"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Add Criterion Button */}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={handleAddCriterion}
                    className="bg-stone-50 hover:bg-stone-100 text-stone-700 font-bold text-xs px-4 py-2 rounded-xl border border-stone-400 transition-all active:scale-95 flex items-center gap-1.5 cursor-pointer"
                  >
                    <Plus size={14} />
                    <span>Add criterion</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Bottom Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="submit"
                className="bg-[#e65100] hover:bg-[#d84315] text-white font-bold text-xs px-7 py-2.5 rounded-full shadow-md active:scale-95 transition-all cursor-pointer"
              >
                Save changes
              </button>
            </div>
          </form>
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
                Subject settings have been updated.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
