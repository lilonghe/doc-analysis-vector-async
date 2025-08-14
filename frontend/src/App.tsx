import React, { useState, useEffect, useCallback } from 'react';
import { Play, RotateCcw, Trash2, Info } from 'lucide-react';
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import SearchPanel from './components/SearchPanel';
import { api } from './api';
import { FileInfo } from './types';

function App() {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [databaseStats, setDatabaseStats] = useState<any>(null);

  // 获取所有文件状态
  const fetchFilesStatus = useCallback(async () => {
    try {
      const response = await api.getAllFilesStatus();
      setFiles(response.files);
    } catch (err) {
      console.error('Failed to fetch files status:', err);
    }
  }, []);

  // 获取数据库统计
  const fetchDatabaseStats = useCallback(async () => {
    try {
      const response = await api.getDatabaseStats();
      setDatabaseStats(response.stats || []);
    } catch (err) {
      console.error('Failed to fetch database stats:', err);
    }
  }, []);

  // 定期更新状态
  useEffect(() => {
    fetchFilesStatus();
    fetchDatabaseStats();
    const interval = setInterval(() => {
      fetchFilesStatus();
      fetchDatabaseStats();
    }, 2000); // 每2秒更新一次
    return () => clearInterval(interval);
  }, [fetchFilesStatus, fetchDatabaseStats]);

  // 上传文件
  const handleFilesSelected = async (fileList: FileList) => {
    setUploading(true);
    setError(null);
    
    try {
      const response = await api.uploadFiles(fileList);
      console.log('Upload successful:', response);
      await fetchFilesStatus(); // 立即更新状态
    } catch (err: any) {
      setError(err.response?.data?.detail || '文件上传失败');
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  // 开始处理所有文件
  const handleProcessAll = async () => {
    setProcessing(true);
    setError(null);

    try {
      const response = await api.processAllFiles();
      console.log('Processing started:', response);
    } catch (err: any) {
      setError(err.response?.data?.detail || '开始处理失败');
      console.error('Process failed:', err);
    } finally {
      setProcessing(false);
    }
  };

  // 删除文件
  const handleDeleteFile = async (fileId: string) => {
    try {
      await api.deleteFile(fileId);
      await fetchFilesStatus(); // 更新列表
      await fetchDatabaseStats(); // 更新统计
    } catch (err: any) {
      setError(err.response?.data?.detail || '删除文件失败');
      console.error('Delete failed:', err);
    }
  };

  // 清空所有文件
  const handleClearAll = async () => {
    if (window.confirm('确定要删除所有文件吗？')) {
      try {
        await Promise.all(files.map(file => api.deleteFile(file.id)));
        await fetchFilesStatus();
        await fetchDatabaseStats();
      } catch (err) {
        setError('清空文件失败');
      }
    }
  };

  // 搜索文档
  const handleSearch = async (query: string) => {
    try {
      const response = await api.searchDocuments(query, 10);
      setSearchResults(response.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || '搜索失败');
      console.error('Search failed:', err);
    }
  };

  // 查看统计信息
  const handleViewStats = () => {
    fetchDatabaseStats();
  };

  const pendingFiles = files.filter(f => f.status === 'pending');
  const processingFiles = files.filter(f => 
    ['uploading', 'parsing', 'chunking', 'embedding', 'storing'].includes(f.status)
  );
  const completedFiles = files.filter(f => f.status === 'completed');
  const errorFiles = files.filter(f => f.status === 'error');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 头部 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            📄 文档向量化处理系统
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            基于 MinerU + 大模型的智能文档解析和向量化存储
          </p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center">
              <Info className="h-5 w-5 text-red-500 mr-2" />
              <p className="text-red-700 dark:text-red-300">{error}</p>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-500 hover:text-red-700"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* 文件上传区域 */}
        <div className="mb-8">
          <FileUpload onFilesSelected={handleFilesSelected} uploading={uploading} />
        </div>

        {/* 操作按钮 */}
        {files.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-3 justify-center">
            <button
              onClick={handleProcessAll}
              disabled={processing || pendingFiles.length === 0}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play className="h-4 w-4 mr-2" />
              {processing ? '处理中...' : `开始处理 (${pendingFiles.length})`}
            </button>

            <button
              onClick={() => fetchFilesStatus()}
              className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              刷新状态
            </button>

            <button
              onClick={handleClearAll}
              disabled={processingFiles.length > 0}
              className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              清空列表
            </button>
          </div>
        )}

        {/* 统计信息 */}
        {files.length > 0 && (
          <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
              <p className="text-blue-600 dark:text-blue-400 text-sm font-medium">等待处理</p>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{pendingFiles.length}</p>
            </div>
            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
              <p className="text-yellow-600 dark:text-yellow-400 text-sm font-medium">处理中</p>
              <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-300">{processingFiles.length}</p>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
              <p className="text-green-600 dark:text-green-400 text-sm font-medium">已完成</p>
              <p className="text-2xl font-bold text-green-700 dark:text-green-300">{completedFiles.length}</p>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
              <p className="text-red-600 dark:text-red-400 text-sm font-medium">失败</p>
              <p className="text-2xl font-bold text-red-700 dark:text-red-300">{errorFiles.length}</p>
            </div>
          </div>
        )}

        {/* 搜索面板 */}
        {completedFiles.length > 0 && (
          <div className="mb-8">
            <SearchPanel
              onSearch={handleSearch}
              onViewStats={handleViewStats}
              searchResults={searchResults}
              databaseStats={databaseStats}
            />
          </div>
        )}

        {/* 文件列表 */}
        <FileList files={files} onDeleteFile={handleDeleteFile} />

        {/* 页脚信息 */}
        <div className="mt-12 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>支持的文件格式: PDF | 最大文件大小: 100MB | 最大并发处理: 3个文件</p>
          <p className="mt-2">
            🚀 使用 MinerU 解析 + OpenAI 智能分块 + ChromaDB 向量存储
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;