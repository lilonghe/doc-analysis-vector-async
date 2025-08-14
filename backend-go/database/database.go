package database

import (
	"context"
	"fmt"
	"log"
	"time"

	"doc-analysis-backend/config"
	"doc-analysis-backend/models"
	
	"gorm.io/driver/postgres"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

func InitDatabase() {
	var err error
	cfg := config.AppConfig
	
	switch cfg.Database.Driver {
	case "postgres":
		DB, err = gorm.Open(postgres.Open(cfg.Database.DSN), &gorm.Config{
			Logger: logger.Default.LogMode(logger.Info),
		})
	case "sqlite":
		DB, err = gorm.Open(sqlite.Open(cfg.Database.DSN), &gorm.Config{
			Logger: logger.Default.LogMode(logger.Info),
		})
	default:
		log.Fatalf("不支持的数据库驱动: %s", cfg.Database.Driver)
	}
	
	if err != nil {
		log.Fatalf("数据库连接失败: %v", err)
	}
	
	// 设置连接池
	sqlDB, err := DB.DB()
	if err != nil {
		log.Fatalf("获取数据库实例失败: %v", err)
	}
	
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)
	
	// 自动迁移
	if err := AutoMigrate(); err != nil {
		log.Fatalf("数据库迁移失败: %v", err)
	}
	
	log.Printf("数据库初始化成功: %s", cfg.Database.Driver)
}

func AutoMigrate() error {
	return DB.AutoMigrate(
		&models.FileRecord{},
		&models.ProcessingLog{},
		&models.Task{},
	)
}

func GetDB() *gorm.DB {
	return DB
}

func CloseDB() error {
	sqlDB, err := DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

// 健康检查
func HealthCheck() error {
	sqlDB, err := DB.DB()
	if err != nil {
		return fmt.Errorf("获取数据库实例失败: %w", err)
	}
	
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	return sqlDB.PingContext(ctx)
}