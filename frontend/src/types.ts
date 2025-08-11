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

export interface DocumentChunk {
  id: string;
  content: string;
  metadata: {
    file_id: string;
    filename: string;
    chunk_index: number;
    chunk_title: string;
    chunk_summary: string;
    chunk_type: string;
    created_at: string;
    content_length: number;
  };
}