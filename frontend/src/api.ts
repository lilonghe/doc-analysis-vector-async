import axios from 'axios';
import { UploadResponse, StatusResponse } from './types';

const API_BASE_URL = '/api';

export const api = {
  // 上传多个文件
  uploadFiles: async (files: FileList): Promise<UploadResponse> => {
    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });

    const response = await axios.post(`${API_BASE_URL}/upload-files`, formData);
    return response.data;
  },

  // 获取所有文件状态
  getAllFilesStatus: async (): Promise<StatusResponse> => {
    const response = await axios.get(`${API_BASE_URL}/files/status`);
    return response.data;
  },

  // 获取单个文件状态
  getFileStatus: async (fileId: string) => {
    const response = await axios.get(`${API_BASE_URL}/files/${fileId}/status`);
    return response.data;
  },

  // 开始处理所有文件
  processAllFiles: async () => {
    const response = await axios.post(`${API_BASE_URL}/process-all`);
    return response.data;
  },

  // 删除文件
  deleteFile: async (fileId: string) => {
    const response = await axios.delete(`${API_BASE_URL}/files/${fileId}`);
    return response.data;
  },

  // 搜索文档
  searchDocuments: async (query: string, nResults: number = 5, fileId?: string) => {
    const response = await axios.post(`${API_BASE_URL}/search`, {
      query,
      n_results: nResults,
      file_id: fileId
    });
    return response.data;
  },

  // 获取数据库统计
  getDatabaseStats: async () => {
    const response = await axios.get(`${API_BASE_URL}/database/stats`);
    return response.data;
  },

  // 获取文件的文档块
  getFileChunks: async (fileId: string) => {
    const response = await axios.get(`${API_BASE_URL}/files/${fileId}/chunks`);
    return response.data;
  },
};