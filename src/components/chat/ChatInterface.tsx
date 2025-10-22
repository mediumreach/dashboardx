import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, FileText, Brain } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import type { Database } from '../../lib/database.types';

type Message = Database['public']['Tables']['chat_messages']['Row'];

interface ChatInterfaceProps {
  sessionId: string | null;
  onNewSession: (sessionId: string) => void;
}

export function ChatInterface({ sessionId, onNewSession }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agentState, setAgentState] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user, profile } = useAuth();

  useEffect(() => {
    if (sessionId) {
      loadMessages(sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadMessages = async (sid: string) => {
    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('session_id', sid)
      .order('created_at', { ascending: true });

    if (error) {
      console.error('Error loading messages:', error);
      return;
    }

    setMessages(data || []);
  };

  const createSession = async () => {
    if (!user || !profile) return null;

    const { data, error } = await supabase
      .from('chat_sessions')
      .insert({
        tenant_id: profile.tenant_id,
        user_id: user.id,
        title: 'New Chat',
      })
      .select()
      .single();

    if (error) {
      console.error('Error creating session:', error);
      return null;
    }

    return data.id;
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !profile) return;

    let currentSessionId = sessionId;
    if (!currentSessionId) {
      const newSessionId = await createSession();
      if (!newSessionId) return;
      currentSessionId = newSessionId;
      onNewSession(newSessionId);
    }

    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setAgentState('Processing your request...');

    try {
      const { error: userMsgError } = await supabase
        .from('chat_messages')
        .insert({
          session_id: currentSessionId,
          tenant_id: profile.tenant_id,
          role: 'user',
          content: userMessage,
        });

      if (userMsgError) throw userMsgError;

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          session_id: currentSessionId!,
          tenant_id: profile.tenant_id,
          role: 'user',
          content: userMessage,
          metadata: {},
          created_at: new Date().toISOString(),
        },
      ]);

      setAgentState('Thinking...');
      await new Promise((resolve) => setTimeout(resolve, 800));

      setAgentState('Searching knowledge base...');
      await new Promise((resolve) => setTimeout(resolve, 1200));

      const assistantResponse = `I've received your message: "${userMessage}". The RAG agent orchestration backend is being implemented next. This will include vector similarity search, LangGraph workflow execution, and streaming responses.`;

      const { error: assistantMsgError } = await supabase
        .from('chat_messages')
        .insert({
          session_id: currentSessionId,
          tenant_id: profile.tenant_id,
          role: 'assistant',
          content: assistantResponse,
          metadata: { agent_state: 'completed' },
        });

      if (assistantMsgError) throw assistantMsgError;

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          session_id: currentSessionId!,
          tenant_id: profile.tenant_id,
          role: 'assistant',
          content: assistantResponse,
          metadata: { agent_state: 'completed' },
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
      setAgentState('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <Brain size={48} className="mb-4 text-gray-400" />
            <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
            <p className="text-sm">Ask questions about your documents or data</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-start gap-2">
                {message.role === 'assistant' && (
                  <Brain size={18} className="mt-0.5 flex-shrink-0" />
                )}
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          </div>
        ))}

        {agentState && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Loader2 size={16} className="animate-spin" />
            <span>{agentState}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 p-4">
        <form onSubmit={sendMessage} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask me anything about your documents..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
