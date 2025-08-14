package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"doc-analysis-backend/config"
)

type ChromaClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

type ChromaCollection struct {
	Name     string                 `json:"name"`
	ID       string                 `json:"id,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

type ChromaAddRequest struct {
	Documents  []string                 `json:"documents"`
	IDs        []string                 `json:"ids"`
	Metadatas  []map[string]interface{} `json:"metadatas,omitempty"`
	Embeddings [][]float32              `json:"embeddings,omitempty"`
}

type ChromaQueryRequest struct {
	QueryTexts  []string `json:"query_texts"`
	NResults    int      `json:"n_results"`
	Where       map[string]interface{} `json:"where,omitempty"`
	Include     []string `json:"include,omitempty"`
}

type ChromaQueryResponse struct {
	IDs       [][]string             `json:"ids"`
	Documents [][]string             `json:"documents"`
	Distances [][]float32            `json:"distances"`
	Metadatas [][]map[string]interface{} `json:"metadatas"`
}

func NewChromaClient() *ChromaClient {
	cfg := config.AppConfig.ChromaDB
	return &ChromaClient{
		BaseURL: fmt.Sprintf("http://%s:%s", cfg.Host, cfg.Port),
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *ChromaClient) CreateCollection(name string) error {
	collection := ChromaCollection{
		Name: name,
		Metadata: map[string]interface{}{
			"description": "文档向量存储集合",
		},
	}
	
	data, err := json.Marshal(collection)
	if err != nil {
		return fmt.Errorf("序列化请求失败: %w", err)
	}
	
	resp, err := c.HTTPClient.Post(
		c.BaseURL+"/api/v1/collections",
		"application/json",
		bytes.NewBuffer(data),
	)
	if err != nil {
		return fmt.Errorf("请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode == http.StatusConflict {
		// 集合已存在，这是正常的
		return nil
	}
	
	if resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("创建集合失败，状态码: %d", resp.StatusCode)
	}
	
	return nil
}

func (c *ChromaClient) AddDocuments(collectionName string, req *ChromaAddRequest) error {
	data, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("序列化请求失败: %w", err)
	}
	
	url := fmt.Sprintf("%s/api/v1/collections/%s/add", c.BaseURL, collectionName)
	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewBuffer(data))
	if err != nil {
		return fmt.Errorf("请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		return fmt.Errorf("添加文档失败，状态码: %d", resp.StatusCode)
	}
	
	return nil
}

func (c *ChromaClient) QueryDocuments(collectionName string, req *ChromaQueryRequest) (*ChromaQueryResponse, error) {
	if req.Include == nil {
		req.Include = []string{"documents", "distances", "metadatas"}
	}
	
	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("序列化请求失败: %w", err)
	}
	
	url := fmt.Sprintf("%s/api/v1/collections/%s/query", c.BaseURL, collectionName)
	resp, err := c.HTTPClient.Post(url, "application/json", bytes.NewBuffer(data))
	if err != nil {
		return nil, fmt.Errorf("请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("查询失败，状态码: %d", resp.StatusCode)
	}
	
	var result ChromaQueryResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}
	
	return &result, nil
}

func (c *ChromaClient) DeleteDocuments(collectionName string, ids []string) error {
	reqData := map[string]interface{}{
		"ids": ids,
	}
	
	data, err := json.Marshal(reqData)
	if err != nil {
		return fmt.Errorf("序列化请求失败: %w", err)
	}
	
	url := fmt.Sprintf("%s/api/v1/collections/%s/delete", c.BaseURL, collectionName)
	req, err := http.NewRequest("DELETE", url, bytes.NewBuffer(data))
	if err != nil {
		return fmt.Errorf("创建请求失败: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("删除文档失败，状态码: %d", resp.StatusCode)
	}
	
	return nil
}

func InitChromaDB() error {
	client := NewChromaClient()
	if err := client.CreateCollection("documents"); err != nil {
		return fmt.Errorf("初始化ChromaDB失败: %w", err)
	}
	log.Println("ChromaDB初始化成功")
	return nil
}