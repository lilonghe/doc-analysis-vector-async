import React from 'react';
import { FileText, Trash2, AlertCircle, CheckCircle, Clock, Loader } from 'lucide-react';
import { FileInfo } from '../types';

interface FileListProps {
  files: FileInfo[];
  onDeleteFile: (fileId: string) => void;
}

const statusIcons = {
  pending: Clock,
  uploading: Loader,
  parsing: Loader,
  chunking: Loader,
  embedding: Loader,
  storing: Loader,
  completed: CheckCircle,
  error: AlertCircle,
};

const statusColors = {
  pending: 'text-gray-500',
  uploading: 'text-blue-500 animate-spin',
  parsing: 'text-yellow-500 animate-spin',
  chunking: 'text-purple-500 animate-spin',
  embedding: 'text-indigo-500 animate-spin',
  storing: 'text-orange-500 animate-spin',
  completed: 'text-green-500',
  error: 'text-red-500',
};

const statusMessages = {
  pending: '等待处理中...',
  uploading: '文件上传中...',
  parsing: 'MinerU解析中...',
  chunking: '智能分块中...',
  embedding: '向量化中...',
  storing: '存储到数据库...',
  completed: '✅ 处理完成',
  error: '❌ 处理失败',
};

const FileList: React.FC<FileListProps> = ({ files, onDeleteFile }) => {
  const getProgressColor = (status: string, progress: number) => {
    if (status === 'error') return 'bg-red-500';
    if (status === 'completed') return 'bg-green-500';
    if (progress > 0) return 'bg-blue-500';
    return 'bg-gray-300';
  };

  if (files.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500 dark:text-gray-400">暂无文件，请先上传PDF文件</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          文件处理列表 ({files.length})
        </h2>
      </div>

      <div className="space-y-3">
        {files.map((file) => {
          const StatusIcon = statusIcons[file.status];
          return (
            <div
              key={file.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <div className="flex-shrink-0 pt-1">
                    <FileText className="h-5 w-5 text-gray-400" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {file.filename}
                    </h3>
                    
                    <div className="mt-2">
                      <div className="flex items-center space-x-2 mb-2">
                        <StatusIcon className={`h-4 w-4 ${statusColors[file.status]}`} />
                        <span className="text-sm text-gray-600 dark:text-gray-300">
                          {file.message || statusMessages[file.status]}
                        </span>
                      </div>
                      
                      {/* 进度条 */}
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(file.status, file.progress)}`}
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                      
                      <div className="flex justify-between items-center mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {file.progress}%
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(file.updated_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => onDeleteFile(file.id)}
                  className="flex-shrink-0 ml-4 p-2 text-gray-400 hover:text-red-500 transition-colors"
                  title="删除文件"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FileList;