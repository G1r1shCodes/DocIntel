import React, { useState, useEffect } from 'react';
import { Bookmark, Search, Trash2, FileText, Calendar } from 'lucide-react';

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
      if (res.ok) {
        const data = await res.json();
        setBookmarks(data);
      }
    } catch (e) {
      console.error('Error fetching bookmarks:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBookmarks();
  }, [searchQuery]);

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/bookmarks/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setBookmarks(bookmarks.filter((b) => b.id !== id));
      }
    } catch (e) {
      console.error('Error deleting bookmark:', e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Search & Filter Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Bookmark className="w-6 h-6 text-amber-400" />
            Saved Knowledge Bookmarks
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Search and organize saved verified answers, citations, and research notes.
          </p>
        </div>

        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search saved bookmarks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
          />
        </div>
      </div>

      {/* Bookmarks Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-sm font-mono">Loading bookmarks...</div>
      ) : bookmarks.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center text-slate-400 space-y-2">
          <Bookmark className="w-10 h-10 mx-auto text-slate-600 mb-2" />
          <p className="font-semibold text-slate-300">No saved bookmarks yet</p>
          <p className="text-xs text-slate-500">
            Click the ⭐ bookmark icon on any AI chat response to save verified answers to your personal library.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bookmarks.map((bm) => (
            <div key={bm.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <span className="px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-semibold rounded-full flex items-center gap-1.5 font-mono">
                    <Bookmark className="w-3 h-3 fill-amber-400" />
                    Saved Answer
                  </span>
                  <button
                    onClick={() => handleDelete(bm.id)}
                    className="p-1 text-slate-500 hover:text-rose-400 transition"
                    title="Delete Bookmark"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <h4 className="text-sm font-bold text-slate-100 leading-snug">"{bm.query}"</h4>
                <p className="text-xs text-slate-300 bg-slate-950/70 p-3 rounded-lg border border-slate-800 leading-relaxed">
                  {bm.answer}
                </p>

                {bm.note && (
                  <div className="text-xs text-cyan-300/90 bg-cyan-500/10 p-2.5 rounded border border-cyan-500/20 font-sans">
                    <span className="font-semibold text-cyan-400 block mb-0.5">Note:</span>
                    {bm.note}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-3 border-t border-slate-800/80 font-mono">
                {bm.filename && (
                  <span className="flex items-center gap-1 text-cyan-400">
                    <FileText className="w-3.5 h-3.5" />
                    {bm.filename}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {new Date(bm.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
