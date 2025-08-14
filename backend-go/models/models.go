package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type FileRecord struct {
	ID       uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	Filename string    `gorm:"not null;size:255" json:"filename"`
	Filepath string    `gorm:"not null;size:500" json:"filepath"`
	FileSize int64     `gorm:"default:0" json:"file_size"`
	MimeType string    `gorm:"size:100" json:"mime_type"`
	
	// 处理状态
	Status   string `gorm:"default:pending;size:50" json:"status"`
	Progress int    `gorm:"default:0" json:"progress"`
	Message  string `gorm:"type:text;default:'等待处理中...'" json:"message"`
	
	// 处理结果
	TotalPages        int     `gorm:"default:0" json:"total_pages"`
	ChunksCount       int     `gorm:"default:0" json:"chunks_count"`
	ProcessingDuration *float64 `json:"processing_duration,omitempty"`
	
	// 错误信息
	ErrorCount int    `gorm:"default:0" json:"error_count"`
	LastError  string `gorm:"type:text" json:"last_error,omitempty"`
	
	// 时间戳
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

func (f *FileRecord) BeforeCreate(tx *gorm.DB) error {
	if f.ID == uuid.Nil {
		f.ID = uuid.New()
	}
	return nil
}

type ProcessingLog struct {
	ID       uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	FileID   uuid.UUID `gorm:"type:uuid;not null" json:"file_id"`
	Stage    string    `gorm:"not null;size:50" json:"stage"`    // parsing, chunking, embedding, storing
	Status   string    `gorm:"not null;size:50" json:"status"`   // started, completed, failed
	Message  string    `gorm:"type:text" json:"message,omitempty"`
	Duration *float64  `json:"duration,omitempty"` // 耗时（秒）
	CreatedAt time.Time `json:"created_at"`
}

func (p *ProcessingLog) BeforeCreate(tx *gorm.DB) error {
	if p.ID == uuid.Nil {
		p.ID = uuid.New()
	}
	return nil
}

// 任务状态
type TaskStatus string

const (
	TaskPending   TaskStatus = "pending"
	TaskRunning   TaskStatus = "running"
	TaskCompleted TaskStatus = "completed"
	TaskFailed    TaskStatus = "failed"
	TaskRetrying  TaskStatus = "retrying"
)

type Task struct {
	ID         string     `gorm:"primary_key;size:100" json:"id"`
	FileID     uuid.UUID  `gorm:"type:uuid;not null" json:"file_id"`
	Type       string     `gorm:"not null;size:50" json:"type"`
	Status     TaskStatus `gorm:"default:pending;size:20" json:"status"`
	Payload    string     `gorm:"type:text" json:"payload,omitempty"`
	ErrorMsg   string     `gorm:"type:text" json:"error_msg,omitempty"`
	RetryCount int        `gorm:"default:0" json:"retry_count"`
	
	CreatedAt time.Time  `json:"created_at"`
	StartedAt *time.Time `json:"started_at,omitempty"`
	EndedAt   *time.Time `json:"ended_at,omitempty"`
}