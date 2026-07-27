"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, ChevronDown, FileText, LogOut, Settings, Users } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import {
  getStoredTeacherSubjectId,
  getSubjects,
  persistTeacherSubjectId,
  type AppSubject,
} from "@/lib/api";

export default function TeacherSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [subjects, setSubjects] = React.useState<AppSubject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = React.useState("");

  React.useEffect(() => {
    if (user?.role !== "teacher") return;

    let ignore = false;

    getSubjects("teacher")
      .then((nextSubjects) => {
        if (ignore) return;
        const storedId = getStoredTeacherSubjectId();
        const selected =
          nextSubjects.find((subject) => subject.id === storedId) ??
          nextSubjects[0];
        setSubjects(nextSubjects);
        if (selected) {
          setSelectedSubjectId(selected.id);
          persistTeacherSubjectId(selected.id);
        }
      })
      .catch(() => {
        if (!ignore) setSubjects([]);
      });

    return () => {
      ignore = true;
    };
  }, [user?.role]);

  const selectedSubject =
    subjects.find((subject) => subject.id === selectedSubjectId) ?? subjects[0];

  return (
    <aside className="w-64 bg-white border-r border-stone-200/60 flex flex-col justify-between fixed h-full z-20">
      <div>
        <div className="p-5 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#e65100]" />
          <h1 className="text-md font-bold tracking-tight text-stone-950">
            Learning Companion
          </h1>
        </div>

        <div className="px-3 mb-6">
          {subjects.length > 0 ? (
            <label className="relative block">
              <select
                value={selectedSubject?.id ?? ""}
                onChange={(event) => {
                  setSelectedSubjectId(event.target.value);
                  persistTeacherSubjectId(event.target.value);
                }}
                className="peer w-full appearance-none p-2.5 pr-8 bg-white border border-stone-200/80 rounded-xl text-[13px] font-bold text-stone-900 outline-none focus:border-[#e65100]/50 focus:ring-2 focus:ring-orange-100 cursor-pointer"
                title="Choose course"
              >
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.displayShort}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={15}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 peer-focus:text-[#e65100]"
              />
              <span className="mt-1 block px-1 text-[10px] font-medium text-stone-400 truncate">
                {selectedSubject?.weeks ?? "0 sessions"}
              </span>
            </label>
          ) : (
            <div className="p-2.5 bg-white border border-stone-200/80 rounded-xl">
              <p className="text-[13px] font-bold text-stone-900 truncate pr-1">
                No course yet
              </p>
              <p className="text-[10px] text-stone-400 font-medium">
                Create a course to begin
              </p>
            </div>
          )}
        </div>

        <nav className="px-3 space-y-5">
          <div>
            <p className="px-2 text-[10px] font-bold text-stone-400 uppercase tracking-wider mb-1.5">
              Teacher
            </p>
            <div className="space-y-0.5">
              <Link
                href="/teacher/dashboard"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] rounded-lg transition-colors ${
                  pathname.startsWith("/teacher/dashboard")
                    ? "font-bold text-[#e65100] bg-[#fff3ed]"
                    : "font-medium text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <CalendarDays size={15} />
                Sessions
              </Link>

              <Link
                href="/teacher/students"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] rounded-lg transition-colors ${
                  pathname.startsWith("/teacher/students")
                    ? "font-bold text-[#e65100] bg-[#fff3ed]"
                    : "font-medium text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <Users size={15} />
                Students
              </Link>

              <Link
                href="/teacher/materials"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] rounded-lg transition-colors ${
                  pathname.startsWith("/teacher/materials")
                    ? "font-bold text-[#e65100] bg-[#fff3ed]"
                    : "font-medium text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <FileText size={15} />
                Materials & prompts
              </Link>

              <Link
                href="/teacher/setting"
                className={`flex items-center gap-2.5 px-3 py-2 text-[14px] rounded-lg transition-colors ${
                  pathname.startsWith("/teacher/setting")
                    ? "font-bold text-[#e65100] bg-[#fff3ed]"
                    : "font-medium text-stone-600 hover:bg-stone-50 hover:text-stone-900"
                }`}
              >
                <Settings size={15} />
                Subject settings
              </Link>
            </div>
          </div>
        </nav>
      </div>

      <div className="p-4 border-t border-stone-100 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold text-stone-900 truncate">
            {user?.name ?? "Teacher"}
          </p>
          <p className="text-[10px] text-stone-400">Teacher</p>
        </div>
        <button
          type="button"
          onClick={logout}
          className="p-2 text-stone-400 hover:text-[#d84315] rounded-lg transition-colors"
          title="Log out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
