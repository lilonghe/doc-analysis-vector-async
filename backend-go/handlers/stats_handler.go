package handlers

import (
	"doc-analysis-backend/database"
	"doc-analysis-backend/models"
	"doc-analysis-backend/utils"

	"github.com/gin-gonic/gin"
)

type StatsHandler struct{}

func NewStatsHandler() *StatsHandler {
	return &StatsHandler{}
}

type DatabaseStats struct {
	ProcessingStats map[string]interface{} `json:"processing_stats"`
	VectorDB        map[string]interface{} `json:"vector_db"`
}

func (h *StatsHandler) GetDatabaseStats(c *gin.Context) {
	db := database.GetDB()

	// 获取基本统计数据 (匹配 Python 版本的 get_processing_statistics)
	var totalFiles int64
	var completedFiles int64 
	var errorFiles int64
	var processingFiles int64
	var pendingFiles int64

	db.Model(&models.FileRecord{}).Count(&totalFiles)
	db.Model(&models.FileRecord{}).Where("status = ?", "completed").Count(&completedFiles)
	db.Model(&models.FileRecord{}).Where("status = ?", "failed").Count(&errorFiles)
	
	// 处理中的文件 (包含多个状态，匹配 Python 版本)
	db.Model(&models.FileRecord{}).Where("status IN ?", []string{"parsing", "chunking", "embedding", "storing", "processing"}).Count(&processingFiles)
	db.Model(&models.FileRecord{}).Where("status = ?", "pending").Count(&pendingFiles)

	// 获取总文档块数量
	var totalChunksResult *int64
	db.Model(&models.FileRecord{}).Select("SUM(chunks_count)").Row().Scan(&totalChunksResult)
	totalChunks := int64(0)
	if totalChunksResult != nil {
		totalChunks = *totalChunksResult
	}

	// 计算成功率
	successRate := float64(0)
	if totalFiles > 0 {
		successRate = float64(completedFiles) / float64(totalFiles) * 100
		// 保留两位小数
		successRate = float64(int(successRate*100)) / 100
	}

	// TODO: 获取向量数据库统计 (需要 ChromaDB 客户端实现)
	vectorStats := map[string]interface{}{
		"error": "无法获取向量数据库统计",
	}

	// 返回与 Python 版本相同的数据结构
	utils.Success(c, map[string]interface{}{
		"stats": map[string]interface{}{
			"total_files":      totalFiles,
			"completed_files":  completedFiles,
			"error_files":      errorFiles,
			"processing_files": processingFiles,
			"pending_files":    pendingFiles,
			"total_chunks":     totalChunks,
			"success_rate":     successRate,
			"vector_db":        vectorStats,
		},
	})
}
