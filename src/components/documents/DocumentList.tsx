import React, { useEffect, useState } from 'react';
import { FileText, Trash2, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import type { Database } from '../../lib/database.types';

type Document = Database['public']['Tables']['documents']['Row'];

export function DocumentList({ refresh }: { refresh?: number }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocuments();
  }, [refresh]);

  const loadDocuments = async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('documents')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error loading documents:', error);
    } else {
      setDocuments(data || []);
    }
    setLoading(false);
  };

  const deleteDocument = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    const { error } = await supabase.from('documents').delete().eq('id', id);

    if (error) {
      console.error('Error deleting document:', error);
    } else {
      loadDocuments();
    }
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={18} className="text-green-600" />;
      case 'failed':
        return <XCircle size={18} className="text-red-600" />;
      case 'processing':
        return <Loader2 size={18} className="text-blue-600 animate-spin" />;
      default:
        return <Clock size={18} className="text-gray-400" />;
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    const colors = {
      pending: 'bg-gray-100 text-gray-700',
      processing: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
    };

    return (
      <span
        className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status]}`}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={32} className="animate-spin text-gray-400" />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <FileText size={48} className="mx-auto mb-4 text-gray-400" />
        <p className="text-lg font-medium">No documents yet</p>
        <p className="text-sm">Upload your first document to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
        >
          <div className="flex-shrink-0">{getStatusIcon(doc.status)}</div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium text-gray-900 truncate">{doc.title}</h3>
              {getStatusBadge(doc.status)}
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              {doc.file_type && (
                <span className="uppercase">{doc.file_type.split('/').pop()}</span>
              )}
              {doc.file_size && (
                <span>{(doc.file_size / 1024).toFixed(2)} KB</span>
              )}
              <span>{new Date(doc.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          <button
            onClick={() => deleteDocument(doc.id)}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
          >
            <Trash2 size={18} />
          </button>
        </div>
      ))}
    </div>
  );
}
