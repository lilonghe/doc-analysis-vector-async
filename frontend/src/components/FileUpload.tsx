import React, { useCallback } from 'react';
import { Upload, FileText, X } from 'lucide-react';

interface FileUploadProps {
  onFilesSelected: (files: FileList) => void;
  uploading: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesSelected, uploading }) => {
  const [dragActive, setDragActive] = React.useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const files = e.dataTransfer.files;
      // 只处理PDF文件
      const pdfFiles = Array.from(files).filter(file => file.type === 'application/pdf');
      if (pdfFiles.length > 0) {
        const fileList = new DataTransfer();
        pdfFiles.forEach(file => fileList.items.add(file));
        onFilesSelected(fileList.files);
      }
    }
  }, [onFilesSelected]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(e.target.files);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
          ${dragActive 
            ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }
          ${uploading ? 'pointer-events-none opacity-50' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={uploading}
        />
        
        <div className="flex flex-col items-center space-y-4">
          <div className="p-4 bg-blue-100 dark:bg-blue-900/30 rounded-full">
            <Upload className={`h-8 w-8 text-blue-600 dark:text-blue-400 ${uploading ? 'animate-bounce' : ''}`} />
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {uploading ? '上传中...' : '上传PDF文件'}
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              拖拽文件到此处，或点击选择多个PDF文件
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              支持批量上传，仅支持PDF格式
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileUpload;