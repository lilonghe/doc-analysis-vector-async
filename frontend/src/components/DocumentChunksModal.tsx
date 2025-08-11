import React from 'react';
import { X } from 'lucide-react';
import { DocumentChunk } from '../types';

interface DocumentChunksModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileName: string;
  chunks: DocumentChunk[];
  isLoading: boolean;
}

const DocumentChunksModal: React.FC<DocumentChunksModalProps> = ({
  isOpen,
  onClose,
  fileName,
  chunks,
  isLoading
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              文档内容分块
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {fileName} - 共 {chunks.length} 个分块
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600 dark:text-gray-400">加载中...</span>
            </div>
          ) : chunks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 dark:text-gray-400">暂无文档块数据</p>
            </div>
          ) : (
            <div className="space-y-4">
              {chunks.map((chunk, index) => (
                <div
                  key={chunk.id}
                  className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-l-4 border-blue-500"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      分块 #{index + 1}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {chunk.metadata.chunk_type}
                    </span>
                  </div>
                  
                  {chunk.metadata.chunk_title && (
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      {chunk.metadata.chunk_title}
                    </h4>
                  )}
                  
                  <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                    {chunk.content}
                  </p>
                  
                  <div className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>长度: {chunk.metadata.content_length} 字符</span>
                    <span>创建时间: {new Date(chunk.metadata.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="w-full bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-md transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentChunksModal;