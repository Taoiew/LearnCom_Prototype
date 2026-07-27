"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  TrendingUp,
  FileText,
  LogOut,
  Search,
  ChevronDown,
  Download,
  Plus,
  X,
} from "lucide-react";

import {
  getStudentDashboardViewModel,
  getStudentMaterialsViewModel,
  type AppSubject,
  type StudentMaterialsViewModel,
} from "@/lib/api";
import StudentSidebar from "@/components/studentsidebar";

export default function StudentMaterials() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<AppSubject>({
    id: "",
    code: "",
    name: "",
    displayShort: "",
    weeks: "",
  });
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [subjectCode, setSubjectCode] = useState("");
  const [viewModel, setViewModel] = useState<StudentMaterialsViewModel>({
    subjectCode: "",
    groups: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let ignore = false;

    async function load() {
      try {
        const dashboard = await getStudentDashboardViewModel();
        const firstSubject = dashboard.subjects[0] ?? selectedSubject;
        const materials = await getStudentMaterialsViewModel(firstSubject.code);
        if (ignore) return;
        setSelectedSubject(firstSubject);
        setViewModel(materials);
      } catch (error) {
        if (!ignore) {
          setLoadError(error instanceof Error ? error.message : "Failed to load materials.");
        }
      } finally {
        if (!ignore) setIsLoading(false);
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, []);

  const [searchQuery, setSearchQuery] = useState("");

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  };

  const handleAddSubjectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`Adding subject with code: ${subjectCode}`);
    setIsAddSubjectModalOpen(false);
    setSubjectCode("");
  };

  const filteredData = viewModel.groups
    .map((group) => {
      const filteredItems = group.items.filter((item) =>
        item.title.toLowerCase().includes(searchQuery.toLowerCase()),
      );

      return {
        ...group,
        items: filteredItems,
      };
    })
    .filter((group) => group.items.length > 0);

  const hasResults = filteredData.length > 0;

  return (
    <div className="flex min-h-screen bg-[#fdfbf7] text-stone-900 font-sans">
      <StudentSidebar />

      {/* RIGHT MAIN CONTENT */}
      <main
        suppressHydrationWarning
        className="flex-1 pl-64 px-8 pt-14 pb-8 relative overflow-hidden text-left"
        style={{
          background:
            "radial-gradient(ellipse 1600px 600px at 70% 0%, #ffd4a8 0%, #ffdfb8 20%, #ffe9cc 40%, #fff2e0 60%, #ffebd6 100%)",
        }}
      >
        <div className="relative z-10 max-w-6xl mx-auto space-y-6">
          {/* Header section */}
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-stone-900 tracking-tight">
                Materials
              </h2>
              <p className="text-xs text-stone-400 mt-1">
                Files and content from every session in this subject.
              </p>
            </div>

            {/* Search Box */}
            <div className="flex items-center gap-3">
              <div className="relative w-64">
                <Search
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
                />
                <input
                  type="text"
                  placeholder="Search materials"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 h-9 bg-white border border-stone-200/80 rounded-full text-xs placeholder:text-stone-300 outline-none focus:border-orange-500/50"
                />
              </div>
            </div>
          </div>

          {/* Content Section */}
          {hasResults ? (
            <div className="space-y-8">
              {filteredData.map((group, groupIdx) => (
                <div key={groupIdx} className="space-y-3">
                  {/* Week Title */}
                  <h3 className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">
                    {group.weekTitle}
                  </h3>

                  {/* List of Files */}
                  <div className="space-y-2.5">
                    {group.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between rounded-xl border border-stone-200/60 bg-white p-4 shadow-sm transition-all hover:shadow-md"
                      >
                        <div className="flex items-center gap-3.5">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-stone-50 border border-stone-100">
                            <FileText className="h-5 w-5 text-stone-400" />
                          </div>
                          <div>
                            <h4 className="font-bold text-stone-900 text-sm">
                              {item.title}
                            </h4>
                            <p className="text-[11px] text-stone-400 font-medium mt-0.5">
                              {item.type} - {item.size} - {item.updatedAt}
                            </p>
                          </div>
                        </div>

                        {/* Download Button */}
                        <a
                          href={item.downloadUrl}
                          className="flex items-center gap-1.5 rounded-full border border-stone-800 bg-white px-4 py-2.5 text-xs font-semibold text-stone-1000 transition-colors hover:bg-stone-50 hover:text-stone-950"
                        >
                          <Download size={13} />
                          Download
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 rounded-xl border border-stone-200/50 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-stone-50 border border-stone-100">
                <Search size={20} className="text-stone-400" />
              </div>
              <h3 className="text-base font-bold text-stone-900">
                No materials match your search
              </h3>
              <p className="mt-1 text-xs text-stone-400">
                Try a different keyword, or clear the search to see everything.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
