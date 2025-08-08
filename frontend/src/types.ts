// API接口类型定义
export interface FileInfo {
  id: string;
  filename: string;
  status: 'pending' | 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'storing' | 'completed' | 'error';
  progress: number;
  message: string;
  updated_at: string;
}

export interface UploadResponse {
  files: Array<{
    id: string;
    filename: string;
    status: string;
  }>;
  message: string;
}

export interface StatusResponse {
  files: FileInfo[];
}