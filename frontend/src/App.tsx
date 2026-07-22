import { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  FileText,
  Bookmark as BookmarkIcon,
  BarChart3,
  Shield,
  Send,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Bot,
  User,
  Trash2,
  Layers
} from 'lucide-react';

import { DocumentViewer } from './components/DocumentViewer';
import { UploadDropzone } from './components/UploadDropzone';
import { AdminAnalytics } from './components/AdminAnalytics';
import { BookmarksView } from './components/BookmarksView';

interface CitationItem {
  citation_id: string;
  filename: string;
  page_number: number;
  heading: string;
  section: string;
  text_snippet: string;
  bbox: { x0: number; y0: number; x1: number; y1: number };
}

interface ChatMessageItem {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  faithfulness_status?: string;
  citations?: CitationItem[];
  timestamp?: string;
}

interface IngestedDoc {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  upload_date: string;
  status: string;
  search_count: number;
}

export function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'documents' | 'bookmarks' | 'analytics'>('chat');
  const [userRole, setUserRole] = useState<'Admin' | 'Tender Specialist' | 'Sales' | 'Engineer' | 'Viewer'>('Admin');
  
  // Chat state
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      role: 'assistant',
      content:
        'Welcome to **DocIntel** — Enterprise AI Document Intelligence Platform.\n\nUpload technical specifications, manuals, spreadsheets, or tenders. Ask questions to get hybrid RAG-retrieved answers backed by cross-encoder re-ranking, faithfulness verification, and precise PDF citation highlights.',
      faithfulness_status: 'FAITHFUL',
      citations: [
        {
          citation_id: 'cit_demo_1',
          filename: 'Transformer_Warranty_Manual.pdf',
          page_number: 1,
          heading: 'Section 4 - Technical Warranty',
          section: 'Page 1',
          text_snippet: 'Standard system warranty includes 5-year full replacement coverage under ISO-9001 certification.',
          bbox: { x0: 50, y0: 120, x1: 520, y1: 180 }
        }
      ]
    }
  ]);

  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);

  // Documents state
  const [documents, setDocuments] = useState<IngestedDoc[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchDocuments = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/documents/');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (e) {
      console.error('Error fetching documents:', e);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleSendQuery = async () => {
    if (!query.trim() || loading) return;

    const userText = query.trim();
    setQuery('');
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chat/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': userRole
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: userText
        })
      });

      if (!res.ok) {
        throw new Error('API server error');
      }

      const data = await res.json();
      if (data.session_id) setSessionId(data.session_id);

      const botMessage: ChatMessageItem = {
        role: 'assistant',
        content: data.answer,
        faithfulness_status: data.faithfulness_status,
        citations: data.citations || []
      };

      setMessages((prev) => [...prev, botMessage]);

      if (data.citations && data.citations.length > 0) {
        setActiveCitation(data.citations[0]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Error communicating with DocIntel backend API. Please ensure backend service is running.',
          faithfulness_status: 'ERROR'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBookmark = async (msg: ChatMessageItem) => {
    try {
      await fetch('http://localhost:8000/api/bookmarks/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': userRole
        },
        body: JSON.stringify({
          query: messages[messages.length - 2]?.content || 'Saved Question',
          answer: msg.content,
          filename: msg.citations?.[0]?.filename,
          note: `Saved under ${userRole} workspace session`
        })
      });
      alert('Answer bookmarked successfully!');
    } catch (e) {
      console.error('Bookmark error:', e);
    }
  };

  const handleDeleteDocument = async (id: number) => {
    if (userRole !== 'Admin') {
      alert('Only Admin users can delete ingested documents.');
      return;
    }
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${id}`, {
        method: 'DELETE',
        headers: { 'X-User-Role': userRole }
      });
      if (res.ok) {
        setDocuments(documents.filter((d) => d.id !== id));
      }
    } catch (e) {
      console.error('Delete document error:', e);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Top Application Header */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg text-slate-100 tracking-tight">DocIntel</span>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded-full font-mono">
                ENTERPRISE V1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Hybrid RAG • Citations • Adaptive Chunking • Multi-Format OCR
            </p>
          </div>
        </div>

        {/* User Role Switcher & Clerk Auth Indicator */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
            <Shield className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-400 hidden md:inline">Clerk Auth Role:</span>
            <select
              value={userRole}
              onChange={(e: any) => setUserRole(e.target.value)}
              className="bg-transparent text-cyan-300 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="Admin" className="bg-slate-900 text-slate-200">Admin</option>
              <option value="Tender Specialist" className="bg-slate-900 text-slate-200">Tender Specialist</option>
              <option value="Sales" className="bg-slate-900 text-slate-200">Sales</option>
              <option value="Engineer" className="bg-slate-900 text-slate-200">Engineer</option>
              <option value="Viewer" className="bg-slate-900 text-slate-200">Viewer</option>
            </select>
          </div>

          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>NVIDIA NIM / Groq</span>
          </div>
        </div>
      </header>

      {/* Main Container Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/60 p-4 flex flex-col justify-between shrink-0 hidden md:flex">
          <div className="space-y-6">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-3 mb-2 font-mono">
                Platform Workspaces
              </div>
              <nav className="space-y-1">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                    activeTab === 'chat'
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-md shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Hybrid RAG Chat</span>
                </button>

                <button
                  onClick={() => setActiveTab('documents')}
                  className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                    activeTab === 'documents'
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-md shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Document Library</span>
                </button>

                <button
                  onClick={() => setActiveTab('bookmarks')}
                  className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                    activeTab === 'bookmarks'
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-md shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <BookmarkIcon className="w-4 h-4" />
                  <span>Saved Bookmarks</span>
                </button>

                <button
                  onClick={() => setActiveTab('analytics')}
                  className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                    activeTab === 'analytics'
                      ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-md shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Admin Analytics</span>
                </button>
              </nav>
            </div>

            {/* Quick Ingest Summary */}
            <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs space-y-2">
              <div className="flex justify-between items-center font-mono text-[11px]">
                <span className="text-slate-400">Indexed Docs:</span>
                <span className="text-cyan-400 font-bold">{documents.length}</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-cyan-400 h-full w-full" />
              </div>
              <p className="text-[10px] text-slate-500">FAISS Dense + BM25 Sparse Active</p>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 text-center font-mono border-t border-slate-800/80 pt-3">
            DocIntel Platform • Built for Enterprise
          </div>
        </aside>

        {/* Content View Workspace */}
        <main className="flex-1 p-6 overflow-auto">
          {activeTab === 'chat' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-7rem)]">
              {/* Left Column: Conversational RAG Interface */}
              <div className="lg:col-span-6 flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                {/* Chat Messages Log */}
                <div className="flex-1 overflow-auto p-4 space-y-4">
                  {messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0 mt-1">
                          <Bot className="w-4 h-4" />
                        </div>
                      )}

                      <div className={`max-w-[85%] space-y-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div
                          className={`p-4 rounded-xl text-xs leading-relaxed ${
                            msg.role === 'user'
                              ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-tr-none shadow-lg'
                              : 'bg-slate-950/80 border border-slate-800 text-slate-200 rounded-tl-none'
                          }`}
                        >
                          {/* Faithfulness Badge */}
                          {msg.role === 'assistant' && msg.faithfulness_status && (
                            <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-800 font-mono text-[10px]">
                              <span
                                className={`px-2 py-0.5 rounded font-semibold flex items-center gap-1 ${
                                  msg.faithfulness_status === 'FAITHFUL'
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                }`}
                              >
                                {msg.faithfulness_status === 'FAITHFUL' ? (
                                  <CheckCircle2 className="w-3 h-3" />
                                ) : (
                                  <AlertTriangle className="w-3 h-3" />
                                )}
                                Faithfulness: {msg.faithfulness_status}
                              </span>

                              <button
                                onClick={() => handleSaveBookmark(msg)}
                                className="text-slate-400 hover:text-amber-400 transition flex items-center gap-1"
                              >
                                <BookmarkIcon className="w-3 h-3" />
                                Bookmark
                              </button>
                            </div>
                          )}

                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>

                        {/* Citation Badges Panel */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="space-y-1.5 pt-1">
                            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                              Verified Document Citations (Click to View & Highlight):
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {msg.citations.map((cit, cIdx) => (
                                <button
                                  key={cIdx}
                                  onClick={() => setActiveCitation(cit)}
                                  className={`citation-badge px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 font-mono cursor-pointer ${
                                    activeCitation?.citation_id === cit.citation_id
                                      ? 'bg-cyan-500/30 border-cyan-400 text-cyan-200'
                                      : ''
                                  }`}
                                >
                                  <FileText className="w-3.5 h-3.5" />
                                  <span>{cit.filename}</span>
                                  <span className="opacity-60">| Page {cit.page_number}</span>
                                  <ExternalLink className="w-3 h-3 text-cyan-400" />
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-1">
                          <User className="w-4 h-4" />
                        </div>
                      )}
                    </div>
                  ))}

                  {loading && (
                    <div className="flex gap-3 items-center text-xs text-slate-400 font-mono py-2">
                      <Bot className="w-5 h-5 text-cyan-400 animate-bounce" />
                      <span>Hybrid Retrieving (FAISS + BM25) & Generating Response...</span>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Query Input Box */}
                <div className="p-4 bg-slate-950 border-t border-slate-800">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSendQuery();
                    }}
                    className="flex space-x-2"
                  >
                    <input
                      type="text"
                      placeholder="Ask any question regarding ingested manuals, specs, tenders..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      disabled={loading}
                      className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-xs text-slate-100 focus:outline-none focus:border-cyan-400 transition"
                    />
                    <button
                      type="submit"
                      disabled={loading || !query.trim()}
                      className="px-5 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl shadow-lg shadow-cyan-500/20 flex items-center space-x-1.5 transition"
                    >
                      <span>Ask</span>
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </form>
                  <p className="text-[10px] text-slate-500 mt-2 font-mono flex items-center justify-between">
                    <span>Guardrails & Query Rewriter Enabled</span>
                    <span>Cross-Encoder Rerank (Top 30 $\rightarrow$ Top 5)</span>
                  </p>
                </div>
              </div>

              {/* Right Column: PDF Citation Highlight Viewer */}
              <div className="lg:col-span-6 h-full">
                <DocumentViewer activeCitation={activeCitation} />
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="space-y-6">
              {/* Upload Dropzone */}
              <UploadDropzone onUploadSuccess={fetchDocuments} userRole={userRole} />

              {/* Ingested Documents List Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                <h3 className="text-base font-semibold text-slate-100 mb-4 flex items-center justify-between">
                  <span>Ingested Enterprise Documents</span>
                  <span className="text-xs text-slate-400 font-mono">{documents.length} Files</span>
                </h3>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase">
                        <th className="py-3 px-4">Filename</th>
                        <th className="py-3 px-4">Type</th>
                        <th className="py-3 px-4">Pages</th>
                        <th className="py-3 px-4">Chunks</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Searches</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-slate-800/40 text-slate-200 transition">
                          <td className="py-3 px-4 font-medium flex items-center space-x-2">
                            <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                            <span>{doc.filename}</span>
                          </td>
                          <td className="py-3 px-4 font-mono">
                            <span className="px-2 py-0.5 bg-slate-800 text-cyan-400 border border-slate-700 rounded text-[10px] uppercase">
                              {doc.file_type}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono">{doc.page_count}</td>
                          <td className="py-3 px-4 font-mono text-cyan-300">{doc.chunk_count}</td>
                          <td className="py-3 px-4 font-mono">
                            <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px]">
                              {doc.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-400">{doc.search_count}</td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => handleDeleteDocument(doc.id)}
                              className="p-1 text-slate-500 hover:text-rose-400 transition"
                              title="Delete File"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'bookmarks' && <BookmarksView userRole={userRole} />}
          {activeTab === 'analytics' && <AdminAnalytics userRole={userRole} />}
        </main>
      </div>
    </div>
  );
}

export default App;
