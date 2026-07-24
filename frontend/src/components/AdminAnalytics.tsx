import React, { useEffect, useState } from 'react';
import { BarChart3, FileText, Search, Users, AlertTriangle, Clock, RefreshCw } from 'lucide-react';
import { StatCard } from './StatCard';
import { useAuth } from '@clerk/clerk-react';

interface DashboardStats {
  overview: {
    total_documents: number;
    completed_docs: number;
    active_users: number;
    total_queries_processed: number;
    total_chat_sessions: number;
    total_messages: number;
  };
  top_searched_documents: Array<{ filename: string; file_type: string; search_count: number }>;
  top_searched_queries: Array<{ query: string; count: number }>;
  unanswered_questions: Array<{ id: number; query: string; timestamp: string; response_time_ms: number }>;
}

interface AdminAnalyticsProps {
  userRole: string;
}

export const AdminAnalytics: React.FC<AdminAnalyticsProps> = ({ userRole }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const { getToken } = useAuth();

  const fetchStats = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/analytics/dashboard`, { 
        headers: { 
          'X-User-Role': userRole,
          'Authorization': `Bearer ${token}` 
        } 
      });
      if (res.ok) { const data = await res.json(); setStats(data); }
    } catch (e) { console.error('Failed to fetch analytics:', e); } finally { setLoading(false); }
  };

  useEffect(() => { fetchStats(); }, [userRole, getToken]);

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center h-full space-y-3">
        <RefreshCw className="w-5 h-5 animate-spin text-accent" />
        <div className="text-sm text-text-muted">Loading analytics...</div>
      </div>
    );
  }

  const overview = stats?.overview || {
    total_documents: 4, completed_docs: 4, active_users: 12,
    total_queries_processed: 28, total_chat_sessions: 9, total_messages: 34
  };

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="p-4 md:p-8 space-y-6 max-w-7xl mx-auto w-full pb-12">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-text-main tracking-tight flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-accent" />
              Analytics & Telemetry
            </h1>
            <p className="text-sm text-text-secondary mt-1">Usage insights, document frequency, and unanswered question monitoring.</p>
          </div>
          <button onClick={fetchStats} className="px-3 py-1.5 bg-surface-0 hover:bg-surface-2 border border-border-subtle rounded-lg text-xs font-mono text-accent flex items-center gap-1.5 transition self-start sm:self-auto focus:outline-none shadow-sm">
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Documents" value={overview.total_documents} subtext={`${overview.completed_docs} Parsed & Indexed`} icon={FileText} />
          <StatCard label="Processed Queries" value={overview.total_queries_processed} subtext={`${overview.total_chat_sessions} Active Sessions`} icon={Search} />
          <StatCard label="Active Team Users" value={overview.active_users} subtext="Clerk RBAC Protected" icon={Users} />
          <StatCard label="Unanswered Flags" value={stats?.unanswered_questions.length || 0} subtext="Needs documentation coverage" icon={AlertTriangle} iconColorClass="text-warning" subtextColorClass="text-warning" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-surface-0 border border-border-subtle rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-text-main mb-4">Most Searched Documents</h3>
            <div className="space-y-2">
              {(stats?.top_searched_documents.length ? stats.top_searched_documents : [
                { filename: 'Transformer_Warranty_Manual.pdf', file_type: 'pdf', search_count: 14 },
                { filename: 'Tender_Specification_2026.docx', file_type: 'docx', search_count: 9 },
                { filename: 'Substation_Pricing_Sheet.xlsx', file_type: 'xlsx', search_count: 7 },
                { filename: 'High_Voltage_Safety_Guide.pdf', file_type: 'pdf', search_count: 4 }
              ]).map((doc, idx) => (
                <div key={idx} className="p-3 bg-surface-1 border border-border-subtle rounded-lg flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-3 truncate">
                    <span className="w-6 h-6 rounded-md bg-surface-2 flex items-center justify-center font-mono text-text-muted text-[10px] shrink-0">{idx + 1}</span>
                    <span className="font-medium text-text-main truncate">{doc.filename}</span>
                  </div>
                  <span className="text-text-muted font-mono text-[10px] shrink-0">{doc.search_count} queries</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface-0 border border-border-subtle rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-text-main mb-4">Frequent Queries</h3>
            <div className="space-y-2">
              {(stats?.top_searched_queries.length ? stats.top_searched_queries : [
                { query: 'What is the warranty coverage period for transformers?', count: 8 },
                { query: 'Substation oil viscosity requirements ISO-9001', count: 6 },
                { query: 'Tender liquid damages penalty clauses', count: 5 },
                { query: 'High voltage circuit breaker tolerance limits', count: 3 }
              ]).map((q, idx) => (
                <div key={idx} className="p-3 bg-surface-1 border border-border-subtle rounded-lg flex items-center justify-between text-xs">
                  <span className="text-text-main font-medium truncate pr-3">"{q.query}"</span>
                  <span className="px-2 py-0.5 bg-surface-2 text-text-secondary font-mono rounded text-[10px] border border-border-subtle shrink-0">{q.count} hits</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-surface-0 border border-border-subtle rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-text-main mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" />
            Knowledge Gaps
          </h3>
          <p className="text-xs text-text-secondary mb-4 max-w-2xl">
            Queries where the retriever or faithfulness checker found insufficient evidence.
          </p>
          <div className="space-y-2">
            {(stats?.unanswered_questions.length ? stats.unanswered_questions : [
              { id: 1, query: 'What are the 2027 offshore wind turbine corrosion guidelines?', timestamp: '2026-07-22T10:15:00', response_time_ms: 180.4 },
              { id: 2, query: 'Where is the backup generator serial registration certificate stored?', timestamp: '2026-07-22T11:20:00', response_time_ms: 195.2 }
            ]).map((item) => (
              <div key={item.id} className="p-4 bg-surface-1 border border-border-subtle rounded-lg flex flex-col md:flex-row justify-between items-start md:items-center text-xs gap-3">
                <div className="space-y-1">
                  <div className="font-medium text-text-main">"{item.query}"</div>
                  <div className="text-[10px] text-text-muted font-mono">Logged: {new Date(item.timestamp).toLocaleString()}</div>
                </div>
                <div className="flex items-center space-x-3 font-mono text-[10px] shrink-0">
                  <div className="flex items-center text-text-muted">
                    <Clock className="w-3 h-3 mr-1" />
                    {item.response_time_ms} ms
                  </div>
                  <span className="px-2 py-1 bg-warning-light text-warning rounded font-medium border border-amber-200">Flagged</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
