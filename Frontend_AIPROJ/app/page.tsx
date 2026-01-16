"use client"

import Link from "next/link";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { 
  FileText, 
  Search, 
  BarChart3, 
  Bot, 
  Brain, 
  FileDown,
  ArrowRight,
  Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { documentsAPI } from "@/lib/api/endpoints";
import AIModel3D from "@/components/hero/AIModel3D";
import TechStackFooter from "@/components/layout/TechStackFooter";

const features = [
  {
    title: "Document Intelligence",
    description: "Upload, manage, and analyze documents with RAG search, Q&A, summarization, and CSV analytics - all in one place",
    icon: FileText,
    href: "/documents",
    gradient: "from-neon-cyan to-neon-purple",
  },
  {
    title: "AI Agents",
    description: "Multi-tool AI agents with intelligent routing for document Q&A, data analysis, and ML predictions",
    icon: Bot,
    href: "/agents",
    gradient: "from-neon-magenta to-neon-pink",
  },
  {
    title: "Machine Learning",
    description: "Train, evaluate, and deploy ML models with real-time predictions and performance metrics",
    icon: Brain,
    href: "/ml",
    gradient: "from-neon-purple to-neon-magenta",
  },
  {
    title: "Export Reports",
    description: "Generate PDF and Markdown reports from RAG insights, analytics, and summaries with custom templates",
    icon: FileDown,
    href: "/export",
    gradient: "from-neon-cyan to-neon-green",
  },
];

export default function LandingPage() {
  // Fetch real stats from backend
  const { data: docsData } = useQuery({
    queryKey: ["documents-stats"],
    queryFn: () => documentsAPI.list({ limit: 1, offset: 0 }),
  });

  const totalDocs = docsData?.pagination.total_count || 0;
  // Support both "success" and "completed" status names
  const successfulDocs = 
    (docsData?.health_summary?.success?.count || 0) + 
    ((docsData?.health_summary as any)?.completed?.count || 0);
  const totalChunks = 
    (docsData?.health_summary?.success?.total_chunks || 0) + 
    ((docsData?.health_summary as any)?.completed?.total_chunks || 0);

  const stats = [
    { label: "Documents Processed", value: totalDocs.toLocaleString(), icon: FileText },
    { label: "Successful Ingestions", value: successfulDocs.toLocaleString(), icon: Sparkles },
    { label: "Vector Chunks", value: totalChunks.toLocaleString(), icon: Search },
  ];

  return (
    <div className="min-h-screen bg-base-bg">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-4">
        {/* 3D AI Animation Background */}
        <div className="absolute inset-0">
          <AIModel3D />
        </div>

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-900/50 to-slate-900"></div>

        <div className="relative z-10 max-w-6xl mx-auto text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6">
              <span className="bg-gradient-to-r from-neon-cyan via-neon-magenta to-neon-purple bg-clip-text text-transparent">
                Enterprise RAG Platform
              </span>
            </h1>
            <p className="text-xl sm:text-2xl text-muted-foreground max-w-3xl mx-auto mb-8">
              Transform documents into intelligence with advanced RAG, analytics, and AI orchestration
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link href="/documents">
              <Button size="lg" className="group">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-16 max-w-4xl mx-auto"
          >
            {stats.map((stat, index) => (
              <Card key={index} className="border-neon-cyan/50">
                <CardContent className="p-6 flex items-center space-x-4">
                  <stat.icon className="h-8 w-8 text-neon-cyan" />
                  <div>
                    <p className="text-3xl font-bold text-neon-cyan">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold mb-4 bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
              Powerful Features
            </h2>
            <p className="text-xl text-muted-foreground">
              Everything you need for intelligent document processing
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Link href={feature.href}>
                  <Card className="h-full group hover:scale-105 transition-all cursor-pointer">
                    <CardHeader>
                      <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:shadow-glow-cyan transition-all`}>
                        <feature.icon className="h-6 w-6 text-white" />
                      </div>
                      <CardTitle className="group-hover:text-neon-cyan transition-colors">
                        {feature.title}
                      </CardTitle>
                      <CardDescription>{feature.description}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Button variant="ghost" className="group-hover:text-neon-cyan">
                        Learn More
                        <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                      </Button>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack Footer */}
      <TechStackFooter />
    </div>
  );
}
