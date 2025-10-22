import React, { useState } from 'react';
import { Sidebar } from '../components/layout/Sidebar';
import { ChatInterface } from '../components/chat/ChatInterface';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { DocumentList } from '../components/documents/DocumentList';
import { FileText, Database, Settings as SettingsIcon } from 'lucide-react';

type View = 'chat' | 'documents' | 'sources' | 'settings';

export function DashboardPage() {
  const [currentView, setCurrentView] = useState<View>('chat');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [documentRefresh, setDocumentRefresh] = useState(0);

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setCurrentView('chat');
  };

  const handleSessionSelect = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setCurrentView('chat');
  };

  const handleUploadComplete = () => {
    setDocumentRefresh((prev) => prev + 1);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        currentSessionId={currentSessionId}
        onSessionSelect={handleSessionSelect}
        onNewChat={handleNewChat}
        onNavigate={setCurrentView}
        currentView={currentView}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {currentView === 'chat' && (
          <div className="flex-1 bg-white">
            <ChatInterface
              sessionId={currentSessionId}
              onNewSession={setCurrentSessionId}
            />
          </div>
        )}

        {currentView === 'documents' && (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-8">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Documents</h1>
                <p className="text-gray-600">
                  Upload and manage your knowledge base documents
                </p>
              </div>

              <div className="mb-8">
                <DocumentUpload onUploadComplete={handleUploadComplete} />
              </div>

              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Your Documents
                </h2>
                <DocumentList refresh={documentRefresh} />
              </div>
            </div>
          </div>
        )}

        {currentView === 'sources' && (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-8">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Data Sources</h1>
                <p className="text-gray-600">
                  Connect external data sources for automated ingestion
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { name: 'Amazon S3', type: 's3', icon: Database },
                  { name: 'SharePoint', type: 'sharepoint', icon: Database },
                  { name: 'Confluence', type: 'confluence', icon: Database },
                  { name: 'Google Drive', type: 'google_drive', icon: Database },
                ].map((source) => (
                  <div
                    key={source.type}
                    className="p-6 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <source.icon size={24} className="text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 mb-1">
                          {source.name}
                        </h3>
                        <p className="text-sm text-gray-600 mb-3">
                          Connect to sync documents automatically
                        </p>
                        <button className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">
                          Configure
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {currentView === 'settings' && (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-8">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
                <p className="text-gray-600">
                  Manage your account and platform preferences
                </p>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
                <div className="p-6">
                  <h3 className="font-semibold text-gray-900 mb-4">
                    Agent Configuration
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Temperature
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        defaultValue="0.7"
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Controls response creativity (0 = focused, 1 = creative)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Max Context Documents
                      </label>
                      <input
                        type="number"
                        defaultValue="5"
                        min="1"
                        max="20"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Maximum number of documents to retrieve per query
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-6">
                  <h3 className="font-semibold text-gray-900 mb-4">
                    Security & Privacy
                  </h3>
                  <div className="space-y-3">
                    <label className="flex items-center gap-3">
                      <input type="checkbox" defaultChecked className="rounded" />
                      <span className="text-sm text-gray-700">
                        Enable Row Level Security (RLS) enforcement
                      </span>
                    </label>
                    <label className="flex items-center gap-3">
                      <input type="checkbox" defaultChecked className="rounded" />
                      <span className="text-sm text-gray-700">
                        Log all data access attempts
                      </span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
