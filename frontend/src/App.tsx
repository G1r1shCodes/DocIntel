import { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  FileText,
  Bookmark as BookmarkIcon,
  BarChart3,
  Shield,
  Send,
  CheckCircle2,
  Bot,
  User,
  Trash2,
  Layers,
  Cpu,
  Menu,
  X,
  AlertTriangle,
  ShieldAlert,
  HelpCircle,
  Check,
  Eye,
  Download
} from 'lucide-react';
import { DocumentViewer } from './components/DocumentViewer';
import { UploadDropzone } from './components/UploadDropzone';
import { AdminAnalytics } from './components/AdminAnalytics';
import { BookmarksView } from './components/BookmarksView';
import { NavButton } from './components/NavButton';
import { EmptyState } from './components/EmptyState';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth } from '@clerk/clerk-react';

interface CitationItem {
  citation_id: string;
  chunk_id?: number | null;
  document_id?: number | null;
  filename: string;
  page_number: number;
  heading: string;
  section: string;
  text_snippet: string;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  page_width?: number | null;
  page_height?: number | null;
}

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 9);
}

interface ChatMessageItem {
  id: string | number;
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { getToken } = useAuth();
  
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      id: 'initial',
      role: 'assistant',
      content:
        'Welcome to DocIntel — Enterprise AI Document Intelligence Engine.\n\nUpload technical specifications, manuals, spreadsheets, or tenders. Ask questions to get hybrid RAG-retrieved answers backed by cross-encoder re-ranking, faithfulness verification, and precise PDF citation highlights.',
      faithfulness_status: 'FAITHFUL',
      citations: [
        {
          citation_id: 'cit_demo_1',
          filename: 'Transformer_Warranty_Manual.pdf',
          page_number: 1,
          heading: 'Section 4.2 - Technical Specifications',
          section: 'Page 1',
          text_snippet: 'Standard system warranty includes 5-year full replacement coverage including surge protection under ISO-9001 certification.',
          bbox: { x0: 32, y0: 290, x1: 588, y1: 400 }
        }
      ]
    }
  ]);

  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);
  const [documents, setDocuments] = useState<IngestedDoc[]>([]);
  const [savedIds, setSavedIds] = useState<Set<string | number>>(new Set());
  const [previewDoc, setPreviewDoc] = useState<IngestedDoc | null>(null);
  const [previewTextContent, setPreviewTextContent] = useState<string | null>(null);
  const [previewTextLoading, setPreviewTextLoading] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchDocuments = async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/documents/`, {
        headers: { 
          'X-User-Role': userRole,
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(Array.isArray(data) ? data : data.documents || []);
      }
    } catch {
      setDocuments([
        {
          id: 1, filename: 'Transformer_Warranty_Manual.pdf', file_type: 'pdf',
          file_size: 245120, page_count: 45, chunk_count: 128,
          upload_date: new Date().toISOString(), status: 'COMPLETED', search_count: 14
        },
        {
          id: 2, filename: 'Tender_Specification_2026.docx', file_type: 'docx',
          file_size: 184000, page_count: 28, chunk_count: 86,
          upload_date: new Date().toISOString(), status: 'COMPLETED', search_count: 9
        },
        {
          id: 3, filename: 'Substation_Pricing_Sheet.xlsx', file_type: 'xlsx',
          file_size: 92100, page_count: 6, chunk_count: 42,
          upload_date: new Date().toISOString(), status: 'COMPLETED', search_count: 7
        }
      ]);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [userRole]);

  const handleSendQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || loading) return;

    const msgId = generateUUID();
    const userMessage: ChatMessageItem = {
      id: msgId, role: 'user', content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/chat/query`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Role': userRole,
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query: userMessage.content, session_id: sessionId, top_k: 5 })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.session_id) setSessionId(data.session_id);
        const assistantMessage: ChatMessageItem = {
          id: generateUUID(), role: 'assistant', content: data.answer,
          faithfulness_status: data.faithfulness_status,
          citations: data.citations || [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, assistantMessage]);
        if (data.citations && data.citations.length > 0) setActiveCitation(data.citations[0]);
      } else {
        throw new Error('API query failed');
      }
    } catch {
        const fallbackMessage: ChatMessageItem = {
          id: generateUUID(), role: 'assistant',
          content: 'Sorry, I encountered an error while processing your question. This could be due to a temporary network issue or the AI service being unavailable. Please try again.\n\nIf the problem persists, ensure the backend server is running and check your API key configuration.',
          faithfulness_status: 'INSUFFICIENT_EVIDENCE',
          citations: [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, fallbackMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (id: number) => {
    if (userRole !== 'Admin') { alert('Deleting documents requires Admin role privileges.'); return; }
    try {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/documents/${id}`, { 
        method: 'DELETE', 
        headers: { 
          'X-User-Role': userRole,
          'Authorization': `Bearer ${token}`
        } 
      });
      if (!res.ok) {
        let errorMsg = 'Failed to delete document';
        try { const err = await res.json(); errorMsg = err.detail || errorMsg; } catch {}
        alert(errorMsg);
        return;
      }
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      alert('Network error: Could not reach the server. The document was not deleted.');
    }
  };

  const closeSidebarOnMobile = () => { if (window.innerWidth < 1024) setSidebarOpen(false); };

  const handleSaveBookmark = async (msg: ChatMessageItem) => {
    if (savedIds.has(msg.id)) return;
    const idx = messages.findIndex((m) => m.id === msg.id);
    const priorUser = messages.slice(0, idx < 0 ? messages.length : idx).reverse().find((m) => m.role === 'user');
    const payload = {
      query: priorUser?.content || 'Saved answer',
      answer: msg.content,
      filename: msg.citations?.[0]?.filename ?? null,
      note: null
    };
    // Optimistic mark; revert on failure.
    setSavedIds((prev) => new Set(prev).add(msg.id));
    try {
      const token = await getToken();
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/bookmarks/`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'X-User-Role': userRole,
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('save failed');
    } catch {
      setSavedIds((prev) => {
        const next = new Set(prev);
        next.delete(msg.id);
        return next;
      });
    }
  };

  const faithMeta = (status?: string) => {
    switch (status) {
      case 'FAITHFUL':
        return { Icon: CheckCircle2, color: 'text-success', label: 'Faithful' };
      case 'INSUFFICIENT_EVIDENCE':
        return { Icon: AlertTriangle, color: 'text-warning', label: 'Insufficient Evidence' };
      case 'BLOCKED':
        return { Icon: ShieldAlert, color: 'text-danger', label: 'Blocked' };
      default:
        return { Icon: HelpCircle, color: 'text-text-muted', label: status || 'Unverified' };
    }
  };

  const docStatusClass = (status: string) => {
    switch ((status || '').toUpperCase()) {
      case 'COMPLETED':
        return 'bg-success-light text-success border-emerald-200';
      case 'FAILED':
        return 'bg-danger-light text-danger border-red-200';
      default:
        return 'bg-warning-light text-warning border-amber-200';
    }
  };

  return (
    <div className="flex flex-col h-[100dvh] bg-surface-0 text-text-main font-sans overflow-hidden">
      {/* HEADER */}
      <header className="h-14 bg-surface-0 flex items-center justify-between px-4 lg:px-6 z-30 shrink-0 border-b border-border-subtle">
        <div className="flex items-center space-x-3">
          <button
            className="lg:hidden p-2 text-text-secondary hover:text-text-main rounded-lg hover:bg-surface-2 transition focus:outline-none"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation menu"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <Layers className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-base tracking-tight text-text-main">DocIntel</span>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-success-light border border-emerald-200 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            <span className="text-success font-medium">NVIDIA NIM / Groq Active</span>
          </div>
          <div className="flex items-center space-x-2 bg-surface-1 p-1 rounded-lg border border-border-subtle">
            <Shield className="w-4 h-4 text-text-muted ml-2" />
            <label htmlFor="role-select" className="sr-only">Select User Role</label>
            <select
              id="role-select"
              value={userRole}
              onChange={(e) => setUserRole(e.target.value as any)}
              className="bg-surface-1 text-text-main text-sm font-medium px-2 py-1 rounded-lg border-transparent focus:outline-none cursor-pointer"
            >
              <option value="Admin">Admin</option>
              <option value="Tender Specialist">Tender Specialist</option>
              <option value="Sales">Sales Engineer</option>
              <option value="Engineer">Field Engineer</option>
              <option value="Viewer">Viewer</option>
            </select>
          </div>
          <SignedIn>
            <UserButton />
          </SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="bg-accent text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-accent/90 transition">Sign In</button>
            </SignInButton>
          </SignedOut>
        </div>
      </header>

      {/* WORKSPACE */}
      <SignedIn>
        <div className="flex flex-1 overflow-hidden relative">
        {sidebarOpen && (
          <div className="fixed inset-0 bg-black/20 z-20 lg:hidden" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
        )}
        
        <aside className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 absolute lg:relative z-20 w-60 h-full bg-surface-0 border-r border-border-subtle flex flex-col justify-between shrink-0 p-4 transition-transform duration-200 ease-in-out`}>
          <div className="space-y-5">
            <nav className="space-y-1">
              <NavButton label="Hybrid RAG Chat" icon={MessageSquare} isActive={activeTab === 'chat'} onClick={() => { setActiveTab('chat'); closeSidebarOnMobile(); }} />
              <NavButton 
                label="Document Library" icon={FileText} isActive={activeTab === 'documents'} 
                onClick={() => { setActiveTab('documents'); closeSidebarOnMobile(); }}
                rightElement={
                  <span className="px-1.5 py-0.5 rounded-md text-[10px] font-mono bg-surface-2 text-text-secondary border border-border-subtle">{documents.length}</span>
                }
              />
              <NavButton label="Saved Bookmarks" icon={BookmarkIcon} isActive={activeTab === 'bookmarks'} onClick={() => { setActiveTab('bookmarks'); closeSidebarOnMobile(); }} />
              <NavButton label="Admin Analytics" icon={BarChart3} isActive={activeTab === 'analytics'} onClick={() => { setActiveTab('analytics'); closeSidebarOnMobile(); }} />
            </nav>

            <div className="p-4 rounded-xl bg-surface-1 border border-border-subtle text-xs space-y-3">
              <div className="flex items-center justify-between text-text-secondary">
                <span className="font-medium">Indexed Docs</span>
                <span className="font-mono text-accent font-semibold">{documents.length}</span>
              </div>
              <div className="w-full bg-surface-2 h-1.5 rounded-full overflow-hidden">
                <div className="bg-accent h-full w-3/4 rounded-full" />
              </div>
              <p className="text-[11px] text-text-muted">FAISS Dense + BM25 Sparse</p>
            </div>
          </div>
        </aside>

        {/* CONTENT AREA */}
        <main className="flex-1 overflow-y-auto lg:overflow-hidden bg-surface-1 relative flex flex-col">
          {/* CHAT TAB */}
          {activeTab === 'chat' && (
            <div className="flex flex-col lg:flex-row h-full w-full overflow-hidden">
              {/* Chat Panel */}
              <div className="w-full lg:w-1/2 flex flex-col h-[60vh] lg:h-full border-b lg:border-b-0 lg:border-r border-border-subtle bg-surface-0">
                <div className="px-5 py-3 border-b border-border-subtle flex items-center justify-between bg-surface-0 shrink-0">
                  <div className="flex items-center space-x-3">
                    <div className="p-1.5 rounded-lg bg-accent-light text-accent">
                      <Bot className="w-4 h-4" />
                    </div>
                    <h2 className="font-semibold text-sm text-text-main">Hybrid RAG Assistant</h2>
                  </div>
                  <div className="hidden sm:flex items-center space-x-2 text-xs text-text-muted">
                    <Cpu className="w-3.5 h-3.5" />
                    <span>Faithfulness Audit Active</span>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 bg-surface-1">
                  {messages.map((msg) => (
                    <div key={msg.id} className={`flex space-x-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center shrink-0">
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                      )}
                      <div className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-accent text-white rounded-tr-sm shadow-sm'
                          : 'bg-surface-0 text-text-main rounded-tl-sm border border-border-subtle shadow-sm'
                      }`}>
                        {msg.role === 'assistant' && (
                          <div className="flex items-center justify-between mb-3 pb-2 border-b border-border-subtle">
                            {msg.faithfulness_status ? (
                              (() => {
                                const { Icon, color, label } = faithMeta(msg.faithfulness_status);
                                return (
                                  <span className={`flex items-center text-[11px] font-medium ${color}`}>
                                    <Icon className="w-3.5 h-3.5 mr-1.5" />
                                    {label}
                                  </span>
                                );
                              })()
                            ) : <span />}
                            {msg.id !== 'initial' && (
                              <button
                                onClick={() => handleSaveBookmark(msg)}
                                disabled={savedIds.has(msg.id)}
                                className={`flex items-center gap-1 text-[11px] font-medium rounded-md px-1.5 py-0.5 transition focus:outline-none ${
                                  savedIds.has(msg.id)
                                    ? 'text-success cursor-default'
                                    : 'text-text-muted hover:text-accent hover:bg-accent-light'
                                }`}
                                title={savedIds.has(msg.id) ? 'Saved to bookmarks' : 'Save to bookmarks'}
                                aria-label={savedIds.has(msg.id) ? 'Saved to bookmarks' : 'Save to bookmarks'}
                              >
                                {savedIds.has(msg.id)
                                  ? <><Check className="w-3.5 h-3.5" />Saved</>
                                  : <><BookmarkIcon className="w-3.5 h-3.5" />Save</>}
                              </button>
                            )}
                          </div>
                        )}
                        {(() => {
                          const content = msg.content;
                          const citations = msg.citations || [];

                          if (citations.length === 0) {
                            return <div className="whitespace-pre-wrap">{content}</div>;
                          }

                          // Render [N] markers as clickable citation badges
                          const regex = /\[(\d+)\]/g;
                          const parts: React.ReactNode[] = [];
                          let lastIndex = 0;
                          let match;

                          while ((match = regex.exec(content)) !== null) {
                            const textBefore = content.slice(lastIndex, match.index);
                            if (textBefore) parts.push(<span key={`t-${lastIndex}`}>{textBefore}</span>);
                            
                            const citIndex = parseInt(match[1], 10) - 1;
                            if (citIndex >= 0 && citIndex < citations.length) {
                              const cit = citations[citIndex];
                              parts.push(
                                <button
                                  key={`c-${match.index}`}
                                  onClick={() => setActiveCitation(cit)}
                                  className={`mx-0.5 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded text-[10px] font-bold cursor-pointer transition focus:outline-none ${
                                    activeCitation?.citation_id === cit.citation_id
                                      ? 'bg-accent text-white shadow-sm'
                                      : 'bg-accent-light text-accent hover:bg-accent hover:text-white'
                                  }`}
                                  title={cit.filename}
                                >
                                  {match[1]}
                                </button>
                              );
                            } else {
                              parts.push(<span key={`t-${match.index}`}>{match[0]}</span>);
                            }
                            lastIndex = regex.lastIndex;
                          }
                          const textAfter = content.slice(lastIndex);
                          if (textAfter) parts.push(<span key={`t-last`}>{textAfter}</span>);

                          // Always show Sources section at the bottom when citations exist
                          return (
                            <div className="whitespace-pre-wrap leading-relaxed">
                              <div>{parts}</div>
                              <div className="mt-3 pt-2 border-t border-border-subtle">
                                <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                                  Sources
                                </span>
                                <div className="flex flex-wrap gap-1.5 mt-1.5">
                                  {citations.map((cit, i) => (
                                    <button
                                      key={`src-${i}`}
                                      onClick={() => setActiveCitation(cit)}
                                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium cursor-pointer transition focus:outline-none ${
                                        activeCitation?.citation_id === cit.citation_id
                                          ? 'bg-accent text-white shadow-sm'
                                          : 'bg-accent-light text-accent hover:bg-accent hover:text-white'
                                      }`}
                                      title={cit.filename}
                                    >
                                      <span className="font-bold">{i + 1}</span>
                                      <span className="truncate max-w-[120px]">{cit.filename}</span>
                                      <span className="opacity-70">p.{cit.page_number}</span>
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-surface-2 border border-border-subtle flex items-center justify-center shrink-0">
                          <User className="w-4 h-4 text-text-secondary" />
                        </div>
                      )}
                    </div>
                  ))}

                  {loading && (
                    <div className="flex items-center space-x-3 p-4 bg-surface-0 border border-border-subtle rounded-2xl max-w-xs text-text-muted text-sm shadow-sm">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span>Analyzing documents...</span>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                <form onSubmit={handleSendQuery} className="p-4 border-t border-border-subtle bg-surface-0 shrink-0">
                  <div className="relative flex items-center">
                    <label htmlFor="query-input" className="sr-only">Type your question</label>
                    <input
                      id="query-input"
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Ask questions about technical manuals, specifications, pricing..."
                      className="w-full bg-surface-1 text-text-main text-sm rounded-xl pl-4 pr-12 py-3 border border-border-subtle focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition placeholder:text-text-muted"
                    />
                    <button
                      type="submit"
                      disabled={loading || !query.trim()}
                      className="absolute right-2 p-2 rounded-lg bg-accent text-white hover:bg-blue-700 disabled:opacity-40 transition shadow-sm focus:outline-none"
                      aria-label="Send message"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              </div>

              {/* PDF Viewer Panel */}
              <div className="w-full lg:w-1/2 h-[50vh] lg:h-full bg-surface-1 p-4 overflow-hidden flex flex-col">
                {activeCitation ? (
                  <DocumentViewer filename={activeCitation.filename} activeCitation={activeCitation} />
                ) : (
                  <EmptyState icon={FileText} title="No Document Selected" description="Click on a citation badge in the chat to view the source document and highlighted text snippet." />
                )}
              </div>
            </div>
          )}

          {/* DOCUMENTS TAB */}
          {activeTab === 'documents' && (
            <div className="h-full overflow-y-auto p-4 md:p-8 space-y-8">
              <div className="max-w-4xl mx-auto space-y-8">
                <div>
                  <h1 className="text-2xl font-bold text-text-main tracking-tight">Document Library</h1>
                  <p className="text-sm text-text-secondary mt-1">
                    Native parsing + Tesseract OCR fallback for PDF, DOCX, XLSX, CSV, TXT, and Images.
                  </p>
                </div>
                <UploadDropzone userRole={userRole} onUploadSuccess={fetchDocuments} />
                <div className="space-y-4">
                  <h2 className="text-base font-semibold text-text-main">Ingested Documents</h2>
                  {documents.length === 0 ? (
                    <EmptyState icon={FileText} title="No Documents Uploaded" description="Upload a document above to begin indexing it into the vector database." />
                  ) : (
                    <div className="bg-surface-0 rounded-xl overflow-hidden border border-border-subtle overflow-x-auto shadow-sm">
                      <table className="w-full text-left text-sm text-text-secondary min-w-[700px]">
                        <thead className="bg-surface-1 text-text-muted font-medium text-xs border-b border-border-subtle">
                          <tr>
                            <th className="px-6 py-3">Filename</th>
                            <th className="px-6 py-3">Type</th>
                            <th className="px-6 py-3">Pages</th>
                            <th className="px-6 py-3">Chunks</th>
                            <th className="px-6 py-3">Status</th>
                            <th className="px-6 py-3 text-center">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle">
                          {documents.map((doc) => (
                            <tr key={doc.id} className="hover:bg-surface-1 transition-colors">
                              <td className="px-6 py-3.5 font-medium text-text-main flex items-center space-x-2.5">
                                <FileText className="w-4 h-4 text-accent shrink-0" />
                                <span className="truncate max-w-[200px] sm:max-w-xs">{doc.filename}</span>
                              </td>
                              <td className="px-6 py-3.5">
                                <span className="px-2 py-0.5 rounded font-mono text-xs uppercase bg-surface-2 border border-border-subtle text-text-secondary">{doc.file_type}</span>
                              </td>
                              <td className="px-6 py-3.5">{doc.page_count}</td>
                              <td className="px-6 py-3.5 font-medium text-accent">{doc.chunk_count}</td>
                              <td className="px-6 py-3.5">
                                <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${docStatusClass(doc.status)}`}>{doc.status}</span>
                              </td>
                              <td className="px-6 py-3.5 text-center">
                                <div className="flex items-center justify-center space-x-1">
                                  <button
                                    onClick={() => { setPreviewTextContent(null); setPreviewTextLoading(false); setPreviewDoc(doc); }}
                                    className="p-2 rounded-lg text-text-muted hover:text-accent hover:bg-accent-light transition focus:outline-none"
                                    title="View document"
                                    aria-label={`View ${doc.filename}`}
                                  >
                                    <Eye className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleDeleteDocument(doc.id)}
                                    className="p-2 rounded-lg text-text-muted hover:text-danger hover:bg-danger-light transition focus:outline-none"
                                    title="Delete document"
                                    aria-label={`Delete ${doc.filename}`}
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'bookmarks' && <BookmarksView userRole={userRole} />}
          {activeTab === 'analytics' && <AdminAnalytics userRole={userRole} />}

          {/* Document Preview Modal */}
          {previewDoc && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
              onClick={() => setPreviewDoc(null)}
            >
              <div
                className="relative w-[90vw] max-w-5xl h-[85vh] bg-surface-0 rounded-2xl shadow-2xl border border-border-subtle flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-border-subtle bg-surface-0 shrink-0">
                  <div className="flex items-center space-x-2.5 min-w-0">
                    <FileText className="w-4 h-4 text-accent shrink-0" />
                    <span className="font-semibold text-sm text-text-main truncate">{previewDoc.filename}</span>
                    <span className="px-2 py-0.5 text-[10px] font-mono bg-accent-light text-accent rounded shrink-0 uppercase">{previewDoc.file_type}</span>
                  </div>
                  <button
                    onClick={() => setPreviewDoc(null)}
                    className="p-2 rounded-lg text-text-muted hover:text-text-main hover:bg-surface-2 transition focus:outline-none"
                    title="Close preview"
                    aria-label="Close document preview"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Modal Body */}
                <div className="flex-1 overflow-hidden bg-surface-1">
                  {(() => {
                    const ft = previewDoc.file_type.toLowerCase();
                    const fileUrl = `${import.meta.env.VITE_API_URL || ''}/api/documents/${previewDoc.id}/file`;

                    // PDF — native browser iframe viewer
                    if (ft === 'pdf') {
                      return (
                        <iframe
                          src={fileUrl}
                          className="w-full h-full border-0"
                          title={`Preview of ${previewDoc.filename}`}
                        />
                      );
                    }

                    // Images — inline img tag
                    if (['png', 'jpg', 'jpeg'].includes(ft)) {
                      return (
                        <div className="flex items-center justify-center h-full p-6 overflow-auto">
                          <img
                            src={fileUrl}
                            alt={previewDoc.filename}
                            className="max-w-full max-h-full object-contain rounded-lg shadow-sm"
                          />
                        </div>
                      );
                    }

                    // Text & CSV — fetch and display as preformatted text
                    if (['txt'].includes(ft)) {
                      if (previewTextContent === null && !previewTextLoading) {
                        setPreviewTextLoading(true);
                        fetch(fileUrl)
                          .then((res) => res.text())
                          .then((text) => {
                            setPreviewTextContent(text);
                            setPreviewTextLoading(false);
                          })
                          .catch(() => {
                            setPreviewTextContent('Failed to load file content.');
                            setPreviewTextLoading(false);
                          });
                      }
                      return (
                        <div className="h-full overflow-auto p-6">
                          {previewTextLoading ? (
                            <div className="flex items-center justify-center h-full">
                              <div className="flex items-center space-x-3 text-text-muted text-sm">
                                <div className="flex space-x-1">
                                  <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '0ms' }} />
                                  <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '150ms' }} />
                                  <div className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span>Loading file content...</span>
                              </div>
                            </div>
                          ) : (
                            <pre className="bg-surface-0 border border-border-subtle rounded-xl p-5 text-sm text-text-main font-mono whitespace-pre-wrap break-words leading-relaxed overflow-auto max-h-full">
                              {previewTextContent}
                            </pre>
                          )}
                        </div>
                      );
                    }

                    // Office formats (docx, doc, xlsx, xls) — download fallback
                    return (
                      <div className="flex items-center justify-center h-full p-8">
                        <div className="text-center space-y-4">
                          <div className="w-16 h-16 rounded-2xl bg-surface-2 border border-border-subtle flex items-center justify-center mx-auto">
                            <FileText className="w-8 h-8 text-text-muted" />
                          </div>
                          <div className="space-y-1">
                            <p className="text-text-main text-sm font-medium">{previewDoc.filename}</p>
                            <p className="text-text-secondary text-xs">Browser preview is not available for <strong className="font-medium text-text-main uppercase">.{ft}</strong> files.</p>
                          </div>
                          <a
                            href={fileUrl}
                            download={previewDoc.filename}
                            className="inline-flex items-center space-x-2 px-5 py-2.5 bg-accent text-white text-sm font-medium rounded-xl hover:bg-accent/90 transition shadow-sm"
                          >
                            <Download className="w-4 h-4" />
                            <span>Download File</span>
                          </a>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
      </SignedIn>
      
      <SignedOut>
        <div className="flex flex-1 items-center justify-center bg-surface-1">
          <div className="text-center space-y-4">
            <ShieldAlert className="w-16 h-16 text-accent mx-auto" />
            <h2 className="text-2xl font-bold text-text-main">Authentication Required</h2>
            <p className="text-text-secondary max-w-md mx-auto">Please sign in to access the DocIntel enterprise intelligence platform.</p>
            <SignInButton mode="modal">
              <button className="bg-accent text-white px-6 py-2.5 rounded-lg font-medium hover:bg-accent/90 transition">
                Sign In to Continue
              </button>
            </SignInButton>
          </div>
        </div>
      </SignedOut>

    </div>
  );
}


export default App;
