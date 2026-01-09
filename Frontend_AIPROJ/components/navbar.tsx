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
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b-2 border-neon-cyan/30 bg-base-surface/95 backdrop-blur-xl px-4 sm:px-6">
      <div className="flex items-center space-x-2 text-sm">
        <Link href="/" className="text-muted-foreground hover:text-neon-cyan transition-colors">
          Dashboard
        </Link>
        {pathname !== "/" && (
          <>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
            <span className="text-neon-cyan font-medium">{currentRoute}</span>
          </>
        )}
      </div>

      <div className="ml-auto flex items-center gap-4">
        {/* Admin Link */}
        {isAdmin && (
          <Link
            href="/admin"
            className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full border-2 border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 transition-colors"
          >
            <Shield className="w-3 h-3 text-purple-400" />
            <span className="text-xs font-medium text-purple-400">Admin</span>
          </Link>
        )}

        {/* Auth Status */}
        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full border-2 border-neon-cyan/30 bg-neon-cyan/10">
              <User className="w-3 h-3 text-neon-cyan" />
              <span className="text-xs font-medium text-neon-cyan">{username}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        ) : (
          <Link href="/login">
            <Button variant="outline" size="sm" className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10">
              <Shield className="w-4 h-4 mr-2" />
              Admin Login
            </Button>
          </Link>
        )}
      </div>
    </header>
  );
}
