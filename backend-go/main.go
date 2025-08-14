package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"doc-analysis-backend/config"
	"doc-analysis-backend/database"
	"doc-analysis-backend/handlers"
	"doc-analysis-backend/middleware"
	"doc-analysis-backend/queue"

	"github.com/gin-gonic/gin"
)

func main() {
	// 初始化配置
	config.InitConfig()

	// 初始化数据库
	database.InitDatabase()
	defer database.CloseDB()

	// 初始化任务队列
	queue.InitQueue()
	defer queue.CloseQueue()

	// 创建 Gin 路由器
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()

	// 添加中间件
	r.Use(middleware.Logger())
	r.Use(middleware.Recovery())
	r.Use(middleware.CORS())

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "healthy",
			"time":   time.Now().Format(time.RFC3339),
		})
	})

	// API 路由
	api := r.Group("/api")
	{
		fileHandler := handlers.NewFileHandler()
		statsHandler := handlers.NewStatsHandler()

		// 文件上传和管理
		api.POST("/upload-files", fileHandler.UploadFiles)
		api.GET("/files/status", fileHandler.GetAllFilesStatus)
		api.GET("/files/:id/status", fileHandler.GetFileStatus)
		api.POST("/files/:id/process", fileHandler.ProcessFile)
		api.POST("/process-all", fileHandler.ProcessAllFiles)
		api.DELETE("/files/:id", fileHandler.DeleteFile)

		// 统计功能
		api.GET("/database/stats", statsHandler.GetDatabaseStats)

		// TODO: 搜索功能
		// api.POST("/search", searchHandler.Search)

		// TODO: 文档块功能
		// api.GET("/files/:id/chunks", fileHandler.GetFileChunks)

		// TODO: 处理日志
		// api.GET("/files/:id/logs", fileHandler.GetProcessingLogs)
	}

	// 启动服务器
	cfg := config.AppConfig
	srv := &http.Server{
		Addr:    cfg.Server.Host + ":" + cfg.Server.Port,
		Handler: r,
	}

	// 启动后台任务处理器
	go func() {
		log.Println("启动任务工作器...")
		queue.StartWorker()
	}()

	// 优雅启动
	go func() {
		log.Printf("服务器启动在 %s:%s", cfg.Server.Host, cfg.Server.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("服务器启动失败: %v", err)
		}
	}()

	// 等待中断信号
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("服务器关闭中...")

	// 优雅关闭
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("服务器强制关闭:", err)
	}

	log.Println("服务器已关闭")
}
