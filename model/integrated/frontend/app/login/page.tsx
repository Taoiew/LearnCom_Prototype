"use client";

import React, { useState } from "react";
import { Mail, Lock, GraduationCap } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setIsSubmitting(true);

    try {
      const loggedInUser = await login(email, password);
      const redirectTo =
        loggedInUser.role === "teacher"
          ? "/teacher/dashboard"
          : "/student/dashboard";
      if (typeof window !== "undefined") {
        window.location.assign(redirectTo);
      }
    } catch (error) {
      setErrorMsg(
        error instanceof Error
          ? error.message
          : "เกิดข้อผิดพลาดในการเข้าสู่ระบบ",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#fdfbf7] text-stone-900 relative overflow-hidden flex flex-col items-center justify-center p-4">
      {/* Soft warm radial ambient glow wash */}
      <div
        className="absolute top-[-250px] left-1/2 -translate-x-1/2 w-[1000px] h-[700px] rounded-full pointer-events-none opacity-70 mix-blend-multiply filter blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(251,146,60,0.22) 0%, rgba(254,215,170,0.08) 50%, rgba(255,255,255,0) 70%)",
        }}
      />

      <div className="relative z-10 w-full max-w-[380px] flex flex-col items-center">
        {/* Top Logo Badge */}
        <div className="inline-flex items-center gap-2 bg-white border border-stone-200/60 shadow-sm rounded-full pl-2 pr-4 py-1.5 mb-12">
          <span className="w-6 h-6 rounded-full bg-orange-50 flex items-center justify-center flex-shrink-0">
            <GraduationCap size={14} className="text-orange-600" />
          </span>
          <span className="text-xs font-bold text-stone-800 tracking-wide">
            Learning Companion
          </span>
        </div>

        {/* Header Content */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-stone-900 tracking-tight mb-2.5">
            Welcome back
          </h1>
          <p className="text-sm text-stone-400 font-normal">
            Prepare before class. Walk in ready.
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="w-full space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="email"
              className="block text-xs font-semibold text-stone-600 pl-1"
            >
              Email address
            </label>
            <div className="relative">
              <Mail
                size={16}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
              />
              <input
              
                id="email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full pl-11 pr-4 h-11 bg-white border border-stone-200 rounded-full text-sm placeholder:text-stone-300 outline-none transition-all focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center pl-1">
              <label
                htmlFor="password"
                className="text-xs font-semibold text-stone-600"
              >
                Password
              </label>
              <a
                href="#"
                className="text-xs font-semibold text-orange-600 hover:text-orange-700 transition-colors"
              >
                Forgot password
              </a>
            </div>
            <div className="relative">
              <Lock
                size={16}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
              />
              <input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-11 pr-4 h-11 bg-white border border-stone-200 rounded-full text-sm placeholder:text-stone-300 outline-none transition-all focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10"
              />
            </div>
          </div>

          {errorMsg && (
            <p className="text-xs text-red-500 font-medium pl-2 animate-pulse">
              {errorMsg}
            </p>
          )}

          {/* Remember Me Checkbox */}
          <div className="flex items-center gap-2 pl-1 pt-1">
            <input
              type="checkbox"
              id="remember"
              className="h-4 w-4 rounded border-stone-300 text-orange-600 focus:ring-orange-500 accent-orange-600 cursor-pointer"
            />
            <label
              htmlFor="remember"
              className="text-xs text-stone-500 font-medium select-none cursor-pointer"
            >
              Remember for 30 days
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full h-11 bg-[#e65100] hover:bg-[#d84315] text-white font-semibold rounded-full shadow-lg shadow-orange-700/20 text-sm mt-4 transition-all active:scale-[0.99] focus:outline-none focus:ring-4 focus:ring-orange-500/20 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Logging in..." : "Log in"}
          </button>
        </form>
      </div>
    </div>
  );
}
