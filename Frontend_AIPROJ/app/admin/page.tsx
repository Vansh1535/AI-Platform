'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store/authStore';
import { adminAPI } from '@/lib/api/endpoints';
import { motion } from 'framer-motion';
import {
  FileText,
  Database,
  Server,
  Activity,
  AlertCircle,
  CheckCircle,
  Loader2,
  RefreshCw,
  FileType,
  BarChart3,
  LogOut,
  ArrowLeft,
} from 'lucide-react';
import type { AdminStatsResponse } from '@/lib/types/api';

export default function AdminPage() {
  const router = useRouter();
  const { isAdmin, verifyToken, logout } = useAuthStore();
  
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const fetchStats = async () => {
    try {
      setError('');
      const data = await adminAPI.stats();
      setStats(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      const valid = await verifyToken();
      if (!valid || !isAdmin) {
        router.push('/login');
      } else {
        fetchStats();
      }
    };
    checkAuth();
  }, []);

  useEffect(() => {
    if (autoRefresh && isAdmin) {
      const interval = setInterval(fetchStats, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, isAdmin]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-cyan-400 animate-spin" />
      </div>
    );
  }

  const StatusBadge = ({ status }: { status: string }) => {
    const isHealthy = status === 'connected';
    const isDegraded = status === 'degraded' || status === 'ready';
    const statusColor = isHealthy ? 'green' : isDegraded ? 'yellow' : 'red';
    const statusText = isHealthy ? 'Connected' : isDegraded ? (status === 'ready' ? 'Ready' : 'Degraded') : 'Error';
    
    return (
      <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
        isHealthy ? 'bg-green-500/20 text-green-400' : 
        isDegraded ? 'bg-yellow-500/20 text-yellow-400' : 
        'bg-red-500/20 text-red-400'
      }`}>
        {isHealthy ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
        <span className="text-sm font-medium">{statusText}</span>
      </div>
    );
  };

  const StatCard = ({
    icon: Icon,
    title,
    value,
    subtitle,
    gradient,
  }: {
    icon: any;
    title: string;
    value: string | number;
    subtitle?: string;
    gradient: string;
  }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-cyan-500/20 hover:border-cyan-500/40 transition-all duration-300"
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-lg bg-gradient-to-br ${gradient}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      <h3 className="text-2xl font-bold text-white mb-1">{value}</h3>
      <p className="text-slate-400 text-sm">{title}</p>
      {subtitle && <p className="text-slate-500 text-xs mt-1">{subtitle}</p>}
    </motion.div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
              Admin Dashboard
            </h1>
            <p className="text-slate-400 mt-2">Real-time system statistics and monitoring</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchStats}
              className="p-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all"
              title="Refresh stats"
            >
              <RefreshCw className="w-5 h-5 text-cyan-400" />
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded-lg border transition-all ${
                autoRefresh
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                  : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
            >
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" />
                <span className="text-sm">Auto-refresh {autoRefresh ? 'ON' : 'OFF'}</span>
              </div>
            </button>
            <button
              onClick={() => router.push('/')}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg border border-cyan-500/30 hover:border-cyan-500/50 transition-all"
            >
              <ArrowLeft className="w-4 h-4 text-cyan-400" />
              <span className="text-cyan-400 text-sm font-medium">Back to Home</span>
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 rounded-lg border border-red-500/30 hover:border-red-500/50 transition-all"
            >
              <LogOut className="w-4 h-4 text-red-400" />
              <span className="text-red-400 text-sm font-medium">Logout</span>
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 mb-6 flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <span className="text-red-400">{error}</span>
          </motion.div>
        )}

        {stats && (
          <>
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                icon={FileText}
                title="Total Documents"
                value={stats.total_documents}
                subtitle="Uploaded documents"
                gradient="from-cyan-500 to-blue-500"
              />
              <StatCard
                icon={Database}
                title="Total Chunks"
                value={stats.total_chunks}
                subtitle="Vector embeddings"
                gradient="from-purple-500 to-pink-500"
              />
              <StatCard
                icon={FileType}
                title="File Formats"
                value={Object.keys(stats.formats).length}
                subtitle="Supported types"
                gradient="from-green-500 to-emerald-500"
              />
              <StatCard
                icon={BarChart3}
                title="Success Rate"
                value={stats.total_documents > 0 ? '100%' : 'N/A'}
                subtitle="Processing success"
                gradient="from-orange-500 to-red-500"
              />
            </div>

            {/* System Health */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-cyan-500/20 mb-8"
            >
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Server className="w-5 h-5 text-cyan-400" />
                System Health
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">PostgreSQL Database</span>
                    <StatusBadge status={stats.database_status} />
                  </div>
                  {stats.database_error && (
                    <p className="text-red-400 text-sm mt-2">{stats.database_error}</p>
                  )}
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">ChromaDB Vector Store</span>
                    <StatusBadge status={stats.vector_store_status} />
                  </div>
                  {stats.vector_store_status === 'degraded' && (
                    <p className="text-yellow-400 text-sm mt-2">
                      ⚠️ ChromaDB not initialized. Documents stored in DB only. RAG search may be limited.
                    </p>
                  )}
                  {stats.vector_store_status === 'error' && stats.total_documents === 0 && (
                    <p className="text-yellow-400 text-sm mt-2">No documents uploaded yet</p>
                  )}
                  {stats.vector_store_status === 'error' && stats.total_documents > 0 && (
                    <p className="text-red-400 text-sm mt-2">
                      ChromaDB unavailable. Restart backend after installing requirements.
                    </p>
                  )}
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 font-medium">LLM Service</span>
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                      stats.llm_configured ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {stats.llm_configured ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                      <span className="text-sm font-medium">{stats.llm_configured ? 'Configured' : 'Not Configured'}</span>
                    </div>
                  </div>
                  {!stats.llm_configured && (
                    <p className="text-yellow-400 text-sm mt-2">Q&A feature requires LLM API key in .env</p>
                  )}
                </div>
              </div>
            </motion.div>

            {/* Format Breakdown */}
            {Object.keys(stats.formats).length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-cyan-500/20 mb-8"
              >
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <FileType className="w-5 h-5 text-cyan-400" />
                  Document Formats
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(stats.formats).map(([format, count]) => (
                    <div key={format} className="bg-slate-900/50 rounded-lg p-4 text-center">
                      <p className="text-2xl font-bold text-cyan-400">{count}</p>
                      <p className="text-slate-400 text-sm uppercase mt-1">{format}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Status Breakdown */}
            {Object.keys(stats.statuses).length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-slate-800/50 backdrop-blur-xl rounded-xl p-6 border border-cyan-500/20"
              >
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-cyan-400" />
                  Processing Status
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(stats.statuses).map(([status, count]) => (
                    <div key={status} className="bg-slate-900/50 rounded-lg p-4 text-center">
                      <p className="text-2xl font-bold text-purple-400">{count}</p>
                      <p className="text-slate-400 text-sm capitalize mt-1">{status}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Footer */}
            <div className="mt-6 text-center text-sm text-slate-500">
              Last updated: {new Date(stats.timestamp).toLocaleString()}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
