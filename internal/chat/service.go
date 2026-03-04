package chat

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

const defaultModel = "gpt-4o-mini"

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type Service struct {
	apiKey   string
	model    string
	client   *http.Client
	messages []Message
	mu       sync.Mutex
}

func NewService(apiKey, model string) *Service {
	model = strings.TrimSpace(model)
	if model == "" {
		model = defaultModel
	}

	return &Service{
		apiKey: apiKey,
		model:  model,
		client: &http.Client{Timeout: 90 * time.Second},
		messages: []Message{
			{
				Role:    "system",
				Content: "You are Gimble Assistant. Be concise, practical, and clear.",
			},
		},
	}
}

func (s *Service) Send(ctx context.Context, userInput string) (string, error) {
	userInput = strings.TrimSpace(userInput)
	if userInput == "" {
		return "", fmt.Errorf("message cannot be empty")
	}

	s.mu.Lock()
	s.messages = append(s.messages, Message{Role: "user", Content: userInput})
	requestMessages := append([]Message(nil), s.messages...)
	s.mu.Unlock()

	body, err := json.Marshal(map[string]any{
		"model":    s.model,
		"messages": requestMessages,
	})
	if err != nil {
		return "", fmt.Errorf("failed to encode request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, "https://api.openai.com/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("openai request failed: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed reading response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("openai API error (%d): %s", resp.StatusCode, strings.TrimSpace(string(raw)))
	}

	var parsed struct {
		Choices []struct {
			Message Message `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}
	if len(parsed.Choices) == 0 {
		return "", fmt.Errorf("openai returned no choices")
	}

	reply := strings.TrimSpace(parsed.Choices[0].Message.Content)
	if reply == "" {
		reply = "(empty response)"
	}

	s.mu.Lock()
	s.messages = append(s.messages, Message{Role: "assistant", Content: reply})
	s.mu.Unlock()

	return reply, nil
}
