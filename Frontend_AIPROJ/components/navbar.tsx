"use client"

import { usePathname, useRouter } from "next/navigation";
import { ChevronRight, LogOut, Shield, User } from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/lib/store/authStore";
import { Button } from "@/components/ui/button";

const routeNames: Record<string, string> = {
  "/": "Home",
  "/documents": "Document Intelligence",
  "/agents": "AI Agents",
  "/ml": "Machine Learning",
  "/export": "Export",
  "/admin": "Admin Dashboard",
  "/login": "Login",
};

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const currentRoute = routeNames[pathname] || "Dashboard";
  const { isAuthenticated, isAdmin, username, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b-2 border-neon-cyan/30 bg-base-surface/95 backdrop-blur-xl pl-16 pr-4 sm:px-6 lg:pl-6">
      <div className="flex items-center space-x-1 sm:space-x-2 text-xs sm:text-sm min-w-0 flex-shrink overflow-hidden">
        <Link href="/" className="text-muted-foreground hover:text-neon-cyan transition-colors hidden md:inline whitespace-nowrap">
          Dashboard
        </Link>
        {pathname !== "/" && (
          <>
            <ChevronRight className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground hidden md:inline flex-shrink-0" />
            <span className="text-neon-cyan font-medium truncate">{currentRoute}</span>
          </>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1 sm:gap-2 md:gap-4 flex-shrink-0">
        {/* Auth Status */}
        {isAuthenticated ? (
          <div className="flex items-center gap-2 sm:gap-3">
            {/* User Badge */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full border-2 border-neon-cyan/30 bg-neon-cyan/10">
              {isAdmin ? (
                <Shield className="w-3 h-3 text-purple-400" />
              ) : (
                <User className="w-3 h-3 text-neon-cyan" />
              )}
              <span className="text-xs font-medium text-neon-cyan">{username}</span>
              {isAdmin && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">Admin</span>
              )}
            </div>
            {/* Admin Dashboard Link */}
            {isAdmin && pathname !== "/admin" && (
              <Link href="/admin">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 px-2 sm:px-3"
                >
                  <Shield className="w-4 h-4 sm:mr-2" />
                  <span className="hidden sm:inline">Dashboard</span>
                </Button>
              </Link>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10 px-2 sm:px-3"
            >
              <LogOut className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Logout</span>
            </Button>
          </div>
        ) : (
          <Link href="/login">
            <Button variant="outline" size="sm" className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 px-2 sm:px-3">
              <Shield className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Admin Login</span>
            </Button>
          </Link>
        )}
      </div>
    </header>
  );
}
