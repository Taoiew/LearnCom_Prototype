"use client";

import TeacherSidebar from "@/components/teachersidebar";

export default function TeacherStudentsPage() {
  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <TeacherSidebar />
      <main
        className="flex-1 pl-64 px-8 pt-14 pb-8 relative overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
              Students
            </h2>
            <p className="text-xs text-stone-400 font-medium mt-1">
              Real student roster data will appear here when a backend endpoint is available.
            </p>
          </div>

          <div className="bg-white/90 border border-stone-200/70 rounded-2xl p-8 text-sm text-stone-500">
            No real students are available yet.
          </div>
        </div>
      </main>
    </div>
  );
}
