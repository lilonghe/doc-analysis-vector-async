package handlers

import (
	"fmt"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"
	"strings"

	"doc-analysis-backend/config"
	"doc-analysis-backend/database"
	"doc-analysis-backend/models"
	"doc-analysis-backend/queue"
	"doc-analysis-backend/utils"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type FileHandler struct{}

func NewFileHandler() *FileHandler {
	return &FileHandler{}
}

func (h *FileHandler) UploadFiles(c *gin.Context) {
	form, err := c.MultipartForm()
	if err != nil {
		utils.BadRequest(c, "无法解析表单数据")
		return
	}

	files := form.File["files"]
	if len(files) == 0 {
		utils.BadRequest(c, "未选择文件")
		return
	}

	cfg := config.AppConfig
	os.MkdirAll(cfg.Upload.Dir, 0755)

	var uploadedFiles []map[string]interface{}
	db := database.GetDB()

	for _, fileHeader := range files {
		// 验证文件类型
		if !isValidFileType(fileHeader.Filename, cfg.Upload.AllowExt) {
			utils.BadRequest(c, fmt.Sprintf("不支持的文件类型: %s", fileHeader.Filename))
			return
		}

		// 验证文件大小
		if fileHeader.Size > cfg.Upload.MaxSize {
			utils.BadRequest(c, fmt.Sprintf("文件过大: %s", fileHeader.Filename))
			return
		}

		// 生成文件ID和路径
		fileID := uuid.New()
		fileExt := filepath.Ext(fileHeader.Filename)
		filePath := filepath.Join(cfg.Upload.Dir, fileID.String()+fileExt)

		// 保存文件
		if err := saveUploadedFile(fileHeader, filePath); err != nil {
			utils.InternalError(c, fmt.Sprintf("保存文件失败: %v", err))
			return
		}

		// 创建数据库记录
		fileRecord := &models.FileRecord{
			ID:       fileID,
			Filename: fileHeader.Filename,
			Filepath: filePath,
			FileSize: fileHeader.Size,
			MimeType: fileHeader.Header.Get("Content-Type"),
			Status:   "pending",
			Progress: 0,
			Message:  "等待处理中...",
		}

		if err := db.Create(fileRecord).Error; err != nil {
			// 删除已保存的文件
			os.Remove(filePath)
			utils.InternalError(c, fmt.Sprintf("创建文件记录失败: %v", err))
			return
		}

		uploadedFiles = append(uploadedFiles, map[string]interface{}{
			"id":       fileID.String(),
			"filename": fileHeader.Filename,
			"status":   "pending",
		})
	}

	utils.SuccessWithMessage(c, fmt.Sprintf("成功上传 %d 个文件", len(uploadedFiles)), map[string]interface{}{
		"files": uploadedFiles,
	})
}

func (h *FileHandler) GetAllFilesStatus(c *gin.Context) {
	db := database.GetDB()
	var files []models.FileRecord

	if err := db.Order("created_at DESC").Find(&files).Error; err != nil {
		utils.InternalError(c, "获取文件列表失败")
		return
	}

	utils.Success(c, map[string]interface{}{
		"files": files,
	})
}

func (h *FileHandler) GetFileStatus(c *gin.Context) {
	fileID := c.Param("id")
	if fileID == "" {
		utils.BadRequest(c, "文件ID不能为空")
		return
	}

	db := database.GetDB()
	var file models.FileRecord

	if err := db.Where("id = ?", fileID).First(&file).Error; err != nil {
		utils.NotFound(c, "文件不存在")
		return
	}

	utils.Success(c, file)
}

func (h *FileHandler) ProcessFile(c *gin.Context) {
	fileID := c.Param("id")
	if fileID == "" {
		utils.BadRequest(c, "文件ID不能为空")
		return
	}

	db := database.GetDB()
	var file models.FileRecord

	if err := db.Where("id = ?", fileID).First(&file).Error; err != nil {
		utils.NotFound(c, "文件不存在")
		return
	}

	// 检查文件状态
	if file.Status == "processing" || file.Status == "completed" {
		utils.BadRequest(c, "文件正在处理或已完成")
		return
	}

	// 更新状态为等待处理
	db.Model(&file).Updates(map[string]interface{}{
		"status":  "pending",
		"message": "已加入处理队列...",
	})

	// 提交到任务队列
	taskInfo, err := queue.EnqueueProcessDocument(fileID)
	if err != nil {
		utils.InternalError(c, fmt.Sprintf("提交任务失败: %v", err))
		return
	}

	utils.SuccessWithMessage(c, "文件已加入处理队列", map[string]interface{}{
		"file_id": fileID,
		"task_id": taskInfo.ID,
	})
}

func (h *FileHandler) ProcessAllFiles(c *gin.Context) {
	db := database.GetDB()
	var files []models.FileRecord

	if err := db.Where("status = ?", "pending").Find(&files).Error; err != nil {
		utils.InternalError(c, "获取待处理文件失败")
		return
	}

	var taskIDs []string
	for _, file := range files {
		taskInfo, err := queue.EnqueueProcessDocument(file.ID.String())
		if err != nil {
			continue
		}
		taskIDs = append(taskIDs, taskInfo.ID)
	}

	utils.SuccessWithMessage(c, fmt.Sprintf("已将 %d 个文件加入处理队列", len(files)), map[string]interface{}{
		"task_ids": taskIDs,
	})
}

func (h *FileHandler) DeleteFile(c *gin.Context) {
	fileID := c.Param("id")
	if fileID == "" {
		utils.BadRequest(c, "文件ID不能为空")
		return
	}

	db := database.GetDB()
	var file models.FileRecord

	if err := db.Where("id = ?", fileID).First(&file).Error; err != nil {
		utils.NotFound(c, "文件不存在")
		return
	}

	// TODO: 删除向量数据库中的数据
	
	// 删除物理文件
	if _, err := os.Stat(file.Filepath); err == nil {
		os.Remove(file.Filepath)
	}

	// 删除数据库记录和相关日志
	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	if err := tx.Where("file_id = ?", fileID).Delete(&models.ProcessingLog{}).Error; err != nil {
		tx.Rollback()
		utils.InternalError(c, "删除处理日志失败")
		return
	}

	if err := tx.Where("file_id = ?", fileID).Delete(&models.Task{}).Error; err != nil {
		tx.Rollback()
		utils.InternalError(c, "删除任务记录失败")
		return
	}

	if err := tx.Delete(&file).Error; err != nil {
		tx.Rollback()
		utils.InternalError(c, "删除文件记录失败")
		return
	}

	tx.Commit()

	utils.SuccessWithMessage(c, "文件删除成功", map[string]interface{}{
		"filename": file.Filename,
	})
}

func isValidFileType(filename string, allowedExt []string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	for _, allowed := range allowedExt {
		if ext == allowed {
			return true
		}
	}
	return false
}

func saveUploadedFile(fh *multipart.FileHeader, dst string) error {
	src, err := fh.Open()
	if err != nil {
		return err
	}
	defer src.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, src)
	return err
}