import React, { useState, useEffect } from 'react';
import { Bookmark, Search, Trash2, FileText, Calendar, RefreshCw } from 'lucide-react';
import { EmptyState } from './EmptyState';

interface SavedBookmark {
  id: number;
  query: string;
  answer: string;
  filename?: string;
  note?: string;
  created_at: string;
}

interface BookmarksViewProps {
  userRole: string;
}

export const BookmarksView: React.FC<BookmarksViewProps> = () => {
  const [bookmarks, setBookmarks] = useState<SavedBookmark[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchBookmarks = async () => {
    setLoading(true);
    try {
      const url = searchQuery
        ? `http://localhost:8000/api/bookmarks/?search=${encodeURIComponent(searchQuery)}`
        : `http://localhost:8000/api/bookmarks/`;
      const res = await fetch(url);
      if (res.ok) { const data = await res.json(); setBookmarks(data); }
    } catch (e) { console.error('Error fetching bookmarks:', e); } finally { setLoading(false); }
  };

  useEffect(() => { fetchBookmarks(); }, [searchQuery]);

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/bookmarks/${id}`, { method: 'DELETE' });
      if (res.ok) setBookmarks(bookmarks.filter((b) => b.id !== id));
    } catch (e) { console.error('Error deleting bookmark:', e); }
  };

  return (
    <div className="p-4 md:p-8 space-y-6 max-w-7xl mx-auto w-full h-full flex flex-col">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-text-main flex items-center gap-2 tracking-tight">
            <Bookmark className="w-6 h-6 text-accent" />
            Knowledge Bookmarks
          </h1>
          <p className="text-sm text-text-secondary mt-1">Search and organize saved verified answers, citations, and research notes.</p>
        </div>
        <div className="relative w-full md:w-80 shrink-0">
          <label htmlFor="bookmark-search" className="sr-only">Search saved bookmarks</label>
          <Search className="w-4 h-4 text-text-muted absolute left-3 top-2.5" />
          <input
            id="bookmark-search"
            type="text"
            placeholder="Search bookmarks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-0 border border-border-subtle rounded-lg pl-9 pr-4 py-2 text-sm text-text-main focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition placeholder:text-text-muted shadow-sm"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 pb-8">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center text-text-muted text-sm space-y-3">
            <RefreshCw className="w-5 h-5 animate-spin text-accent" />
            <span>Loading bookmarks...</span>
          </div>
        ) : bookmarks.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <EmptyState icon={Bookmark} title="No Bookmarks Found" description="Click the bookmark icon on any AI chat response to save verified answers to your personal library." />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 auto-rows-max">
            {bookmarks.map((bm) => (
              <div key={bm.id} className="bg-surface-0 border border-border-subtle rounded-xl p-5 shadow-sm flex flex-col justify-between space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <span className="px-2.5 py-1 bg-accent-light border border-blue-200 text-accent text-[10px] font-medium rounded-full flex items-center gap-1.5 font-mono">
                      <Bookmark className="w-3 h-3" />
                      Saved Answer
                    </span>
                    <button
                      onClick={() => handleDelete(bm.id)}
                      className="p-1.5 text-text-muted hover:text-danger hover:bg-danger-light rounded-md transition focus:outline-none"
                      title="Delete Bookmark"
                      aria-label="Delete Bookmark"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <h3 className="text-sm font-semibold text-text-main leading-snug">"{bm.query}"</h3>
                  <div className="text-sm text-text-secondary bg-surface-1 p-3.5 rounded-lg border border-border-subtle leading-relaxed whitespace-pre-wrap">
                    {bm.answer}
                  </div>
                  {bm.note && (
                    <div className="text-sm text-accent bg-accent-light p-3 rounded-lg border border-blue-200">
                      <span className="font-semibold text-accent block mb-1">Note</span>
                      <span className="text-text-secondary">{bm.note}</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between text-[11px] text-text-muted pt-4 mt-2 border-t border-border-subtle font-mono">
                  {bm.filename && (
                    <span className="flex items-center gap-1.5 truncate max-w-[200px]" title={bm.filename}>
                      <FileText className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{bm.filename}</span>
                    </span>
                  )}
                  <span className="flex items-center gap-1.5 shrink-0 ml-auto">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(bm.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
