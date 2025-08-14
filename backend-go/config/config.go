package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Server struct {
		Host string
		Port string
	}

	Database struct {
		Driver string
		DSN    string
	}

	Redis struct {
		Host     string
		Port     string
		Password string
		DB       int
	}

	ChromaDB struct {
		Host string
		Port string
	}

	Upload struct {
		Dir      string
		MaxSize  int64
		AllowExt []string
	}
}

var AppConfig *Config

func InitConfig() {
	// 加载 .env 文件
	if err := godotenv.Load(); err != nil {
		log.Printf("未找到 .env 文件，使用环境变量: %v", err)
	}

	AppConfig = &Config{
		Server: struct {
			Host string
			Port string
		}{
			Host: getEnv("HOST", "0.0.0.0"),
			Port: getEnv("PORT", "8080"),
		},
		Database: struct {
			Driver string
			DSN    string
		}{
			Driver: getEnv("DATABASE_DRIVER", "sqlite"),
			DSN:    getEnv("DATABASE_URL", "./data.db"),
		},
		Redis: struct {
			Host     string
			Port     string
			Password string
			DB       int
		}{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       0,
		},
		ChromaDB: struct {
			Host string
			Port string
		}{
			Host: getEnv("CHROMA_HOST", "localhost"),
			Port: getEnv("CHROMA_PORT", "8000"),
		},
		Upload: struct {
			Dir      string
			MaxSize  int64
			AllowExt []string
		}{
			Dir:      "./uploads",
			MaxSize:  100 * 1024 * 1024, // 100MB
			AllowExt: []string{".pdf"},
		},
	}

	log.Printf("配置加载成功")
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}