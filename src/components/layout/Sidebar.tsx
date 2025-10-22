import React, { useEffect, useState } from 'react';
import { MessageSquare, Plus, Settings, LogOut, FileText, Database } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import type { Database as DB } from '../../lib/database.types';

type ChatSession = DB['public']['Tables']['chat_sessions']['Row'];

interface SidebarProps {
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: () => void;
  onNavigate: (view: 'chat' | 'documents' | 'sources' | 'settings') => void;
  currentView: string;
}

export function Sidebar({
  currentSessionId,
  onSessionSelect,
  onNewChat,
  onNavigate,
  currentView,
}: SidebarProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const { signOut, profile } = useAuth();

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    const { data, error } = await supabase
      .from('chat_sessions')
      .select('*')
      .order('updated_at', { ascending: false })
      .limit(20);

    if (error) {
      console.error('Error loading sessions:', error);
      return;
    }

    setSessions(data || []);
  };

  const handleNewChat = () => {
    onNewChat();
    loadSessions();
  };

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-screen">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
            <MessageSquare size={18} />
          </div>
          <div>
            <h1 className="font-semibold">RAG Platform</h1>
            <p className="text-xs text-gray-400">{profile?.full_name}</p>
          </div>
        </div>
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-2">
            Navigation
          </h3>
          <nav className="space-y-1">
            <button
              onClick={() => onNavigate('chat')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                currentView === 'chat'
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <MessageSquare size={18} />
              <span>Chat</span>
            </button>
            <button
              onClick={() => onNavigate('documents')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                currentView === 'documents'
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <FileText size={18} />
              <span>Documents</span>
            </button>
            <button
              onClick={() => onNavigate('sources')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                currentView === 'sources'
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <Database size={18} />
              <span>Data Sources</span>
            </button>
          </nav>
        </div>

        {sessions.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-2">
              Recent Chats
            </h3>
            <div className="space-y-1">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => onSessionSelect(session.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors truncate ${
                    currentSessionId === session.id
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-300 hover:bg-gray-800'
                  }`}
                >
                  {session.title}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-2 border-t border-gray-800">
        <button
          onClick={() => onNavigate('settings')}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors mb-1 ${
            currentView === 'settings'
              ? 'bg-gray-800 text-white'
              : 'text-gray-300 hover:bg-gray-800'
          }`}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
        <button
          onClick={signOut}
          className="w-full flex items-center gap-2 px-3 py-2 text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
