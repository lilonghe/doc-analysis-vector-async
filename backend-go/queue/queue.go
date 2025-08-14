package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"doc-analysis-backend/config"
	"doc-analysis-backend/database"
	"doc-analysis-backend/models"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"
)

var (
	Client *asynq.Client
	Server *asynq.Server
)

const (
	TaskProcessDocument = "process_document"
)

type TaskPayload struct {
	FileID string `json:"file_id"`
}

func InitQueue() {
	cfg := config.AppConfig.Redis
	
	redisOpt := asynq.RedisClientOpt{
		Addr:     fmt.Sprintf("%s:%s", cfg.Host, cfg.Port),
		Password: cfg.Password,
		DB:       cfg.DB,
	}
	
	Client = asynq.NewClient(redisOpt)
	
	Server = asynq.NewServer(redisOpt, asynq.Config{
		Concurrency: 10,
		Queues: map[string]int{
			"critical": 6,
			"default":  3,
			"low":      1,
		},
		RetryDelayFunc: func(n int, e error, t *asynq.Task) time.Duration {
			return time.Duration(n) * time.Second
		},
	})
	
	log.Println("任务队列初始化成功")
}

func EnqueueProcessDocument(fileID string) (*asynq.TaskInfo, error) {
	payload := TaskPayload{FileID: fileID}
	data, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("序列化任务载荷失败: %w", err)
	}
	
	task := asynq.NewTask(TaskProcessDocument, data)
	info, err := Client.Enqueue(task, asynq.MaxRetry(3), asynq.Queue("default"))
	if err != nil {
		return nil, fmt.Errorf("任务入队失败: %w", err)
	}
	
	// 记录任务到数据库
	taskRecord := &models.Task{
		ID:     info.ID,
		FileID: uuid.MustParse(fileID),
		Type:   TaskProcessDocument,
		Status: models.TaskPending,
	}
	
	db := database.GetDB()
	if err := db.Create(taskRecord).Error; err != nil {
		log.Printf("任务记录创建失败: %v", err)
	}
	
	return info, nil
}

func StartWorker() {
	mux := asynq.NewServeMux()
	mux.HandleFunc(TaskProcessDocument, HandleProcessDocument)
	
	log.Println("任务工作器启动中...")
	if err := Server.Run(mux); err != nil {
		log.Fatalf("任务工作器启动失败: %v", err)
	}
}

func HandleProcessDocument(ctx context.Context, t *asynq.Task) error {
	var payload TaskPayload
	if err := json.Unmarshal(t.Payload(), &payload); err != nil {
		return fmt.Errorf("任务载荷解析失败: %w", err)
	}
	
	db := database.GetDB()
	
	// 更新任务状态
	now := time.Now()
	taskID, _ := asynq.GetTaskID(ctx)
	taskUpdate := map[string]interface{}{
		"status":     models.TaskRunning,
		"started_at": &now,
	}
	db.Model(&models.Task{}).Where("id = ?", taskID).Updates(taskUpdate)
	
	// 更新文件状态
	fileID := uuid.MustParse(payload.FileID)
	db.Model(&models.FileRecord{}).Where("id = ?", fileID).Updates(map[string]interface{}{
		"status":  "processing",
		"message": "正在处理文档...",
	})
	
	log.Printf("开始处理文档: %s", payload.FileID)
	
	// 这里是实际的文档处理逻辑
	if err := processDocument(payload.FileID); err != nil {
		// 任务失败
		endTime := time.Now()
		taskID, _ := asynq.GetTaskID(ctx)
		db.Model(&models.Task{}).Where("id = ?", taskID).Updates(map[string]interface{}{
			"status":    models.TaskFailed,
			"ended_at":  &endTime,
			"error_msg": err.Error(),
		})
		
		db.Model(&models.FileRecord{}).Where("id = ?", fileID).Updates(map[string]interface{}{
			"status":      "error",
			"message":     fmt.Sprintf("处理失败: %v", err),
			"error_count": gorm.Expr("error_count + 1"),
			"last_error":  err.Error(),
		})
		
		return err
	}
	
	// 任务成功
	endTime := time.Now()
	taskID, _ = asynq.GetTaskID(ctx)
	db.Model(&models.Task{}).Where("id = ?", taskID).Updates(map[string]interface{}{
		"status":   models.TaskCompleted,
		"ended_at": &endTime,
	})
	
	db.Model(&models.FileRecord{}).Where("id = ?", fileID).Updates(map[string]interface{}{
		"status":   "completed",
		"progress": 100,
		"message":  "处理完成",
	})
	
	log.Printf("文档处理完成: %s", payload.FileID)
	return nil
}

func processDocument(fileID string) error {
	// TODO: 实现实际的文档处理逻辑
	// 1. 解析PDF
	// 2. 文本分块
	// 3. 生成向量嵌入
	// 4. 存储到ChromaDB
	
	// 模拟处理时间
	time.Sleep(5 * time.Second)
	
	return nil
}

func GetRedisClient() *redis.Client {
	cfg := config.AppConfig.Redis
	return redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%s", cfg.Host, cfg.Port),
		Password: cfg.Password,
		DB:       cfg.DB,
	})
}

func CloseQueue() {
	if Client != nil {
		Client.Close()
	}
	if Server != nil {
		Server.Stop()
		Server.Shutdown()
	}
}