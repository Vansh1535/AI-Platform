'use client';

import { motion } from 'framer-motion';
import {
  SiNextdotjs,
  SiReact,
  SiTypescript,
  SiTailwindcss,
  SiPython,
  SiFastapi,
  SiPostgresql,
  SiRedis,
  SiOpenai,
  SiDocker,
} from 'react-icons/si';
import { Database, Cpu, Sparkles, Zap, Globe, Server } from 'lucide-react';

const techStacks = [
  {
    category: 'Frontend',
    color: 'from-cyan-400 to-blue-500',
    items: [
      { name: 'Next.js 14', icon: SiNextdotjs },
      { name: 'React 18', icon: SiReact },
      { name: 'TypeScript', icon: SiTypescript },
      { name: 'Tailwind CSS', icon: SiTailwindcss },
      { name: 'Framer Motion', icon: Zap },
      { name: 'TanStack Query', icon: Database },
    ],
  },
  {
    category: 'Backend',
    color: 'from-purple-400 to-pink-500',
    items: [
      { name: 'Python 3.11+', icon: SiPython },
      { name: 'FastAPI', icon: SiFastapi },
      { name: 'PostgreSQL', icon: SiPostgresql },
      { name: 'Redis', icon: SiRedis },
      { name: 'Celery', icon: Server },
      { name: 'ChromaDB', icon: Database },
    ],
  },
  {
    category: 'AI & ML',
    color: 'from-green-400 to-emerald-500',
    items: [
      { name: 'OpenAI GPT-4', icon: SiOpenai },
      { name: 'Gemini', icon: Sparkles },
      { name: 'Ollama', icon: Cpu },
      { name: 'LangChain', icon: Globe },
      { name: 'scikit-learn', icon: Cpu },
    ],
  },
];

export default function TechStackFooter() {
  return (
    <footer className="bg-gradient-to-br from-slate-900 via-purple-900/30 to-slate-900 border-t border-cyan-500/20 py-12">
      <div className="container mx-auto px-6">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-10"
        >
          <h2 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400 mb-2">
            Powered By Modern Tech Stack
          </h2>
          <p className="text-slate-400">
            Built with cutting-edge technologies for enterprise-grade performance
          </p>
        </motion.div>

        {/* Tech Stack Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {techStacks.map((stack, stackIndex) => (
            <motion.div
              key={stack.category}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: stackIndex * 0.1 }}
              className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-cyan-500/20 hover:border-cyan-500/40 transition-all duration-300"
            >
              <h3
                className={`text-xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r ${stack.color}`}
              >
                {stack.category}
              </h3>
              <div className="space-y-3">
                {stack.items.map((tech, techIndex) => (
                  <motion.div
                    key={tech.name}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: stackIndex * 0.1 + techIndex * 0.05 }}
                    className="flex items-center gap-3 text-slate-300 hover:text-cyan-400 transition-colors group"
                  >
                    <div className="p-2 bg-slate-900/50 rounded-lg group-hover:bg-cyan-500/10 transition-colors">
                      <tech.icon className="w-5 h-5" />
                    </div>
                    <span className="text-sm font-medium">{tech.name}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Footer Bottom */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="border-t border-slate-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4"
        >
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-purple-500 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
              Enterprise RAG Platform
            </span>
          </div>
          
          <div className="flex items-center gap-6 text-sm text-slate-400">
            <span>© 2026 All rights reserved</span>
            <span>•</span>
            <span>Built with ❤️ for enterprise AI</span>
          </div>
        </motion.div>
      </div>
    </footer>
  );
}
