import React from 'react';
import { Search, Filter, Database } from 'lucide-react';

interface SearchPanelProps {
  onSearch: (query: string) => void;
  onViewStats: () => void;
  searchResults?: any[];
  databaseStats?: any;
}

const SearchPanel: React.FC<SearchPanelProps> = ({ 
  onSearch, 
  onViewStats, 
  searchResults = [], 
  databaseStats 
}) => {
  const [query, setQuery] = React.useState('');
  const [showResults, setShowResults] = React.useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
      setShowResults(true);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          文档搜索与统计
        </h3>
        <button
          onClick={onViewStats}
          className="inline-flex items-center px-3 py-2 text-sm bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
        >
          <Database className="h-4 w-4 mr-2" />
          数据库统计
        </button>
      </div>

      {/* 搜索表单 */}
      <form onSubmit={handleSearch} className="mb-4">
        <div className="flex space-x-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索文档内容..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            搜索
          </button>
        </div>
      </form>

      {/* 数据库统计 */}
      {databaseStats && (
        <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">数据库统计</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">总文件数:</span>
              <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                {databaseStats.total_files || 0}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">总文档块:</span>
              <span className="ml-2 font-semibold text-gray-900 dark:text-white">
                {databaseStats.total_chunks || 0}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 搜索结果 */}
      {showResults && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
            搜索结果 ({searchResults.length} 个)
          </h4>
          
          {searchResults.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>没有找到相关内容</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {searchResults.map((result, index) => (
                <div
                  key={index}
                  className="p-3 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700/50"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h5 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {result.metadata?.filename || '未知文件'}
                    </h5>
                    <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                      相似度: {(1 - result.distance).toFixed(2)}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
                    {result.content}
                  </p>
                  
                  {result.metadata?.chunk_title && (
                    <div className="mt-2 text-xs text-blue-600 dark:text-blue-400">
                      章节: {result.metadata.chunk_title}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchPanel;