/**
 * AIAssistant — In-app AI assistant with smart suggestions.
 *
 * Provides:
 * - Chat interface for AI conversations
 * - Context-aware suggestions
 * - Command execution via natural language
 * - Response streaming (simulated)
 * - Conversation history
 * - Smart actions based on current context
 */

import { EventEmitter } from "events";

export interface AIMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  context?: AIMessageContext;
  suggestions?: AISuggestion[];
}

export interface AIMessageContext {
  activeFile?: string;
  activeWorkspace?: string;
  selection?: string;
  recentCommands?: string[];
}

export interface AISuggestion {
  id: string;
  type: "action" | "navigation" | "command" | "info";
  label: string;
  description: string;
  command?: string;
  confidence: number; // 0-1
}

export interface AIConversation {
  id: string;
  title: string;
  messages: AIMessage[];
  createdAt: number;
  updatedAt: number;
  context: AIMessageContext;
}

export interface AIResponse {
  message: AIMessage;
  suggestions: AISuggestion[];
  actions: AIAction[];
}

export interface AIAction {
  type: "navigate" | "command" | "open-file" | "search" | "execute";
  target: string;
  params?: Record<string, unknown>;
}

export interface AIAssistantState {
  conversations: AIConversation[];
  activeConversation: string | null;
  isTyping: boolean;
  lastResponse: AIMessage | null;
}

export class AIAssistant extends EventEmitter {
  private conversations: Map<string, AIConversation> = new Map();
  private activeConversationId: string | null = null;
  private isTyping = false;
  private context: AIMessageContext = {};
  private commandHistory: string[] = [];
  private maxHistory = 50;

  constructor() {
    super();
  }

  /**
   * Create a new conversation.
   */
  createConversation(title?: string): AIConversation {
    const conversation: AIConversation = {
      id: `conv-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      title: title || `Chat ${new Date().toLocaleTimeString()}`,
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      context: { ...this.context },
    };

    this.conversations.set(conversation.id, conversation);
    this.activeConversationId = conversation.id;
    this.emit("conversation-created", conversation);

    return conversation;
  }

  /**
   * Get a conversation by ID.
   */
  getConversation(id: string): AIConversation | undefined {
    return this.conversations.get(id);
  }

  /**
   * Get all conversations.
   */
  getConversations(): AIConversation[] {
    return Array.from(this.conversations.values()).sort(
      (a, b) => b.updatedAt - a.updatedAt
    );
  }

  /**
   * Set the active conversation.
   */
  setActiveConversation(id: string | null): void {
    this.activeConversationId = id;
    this.emit("active-conversation-changed", id);
  }

  /**
   * Get the active conversation.
   */
  getActiveConversation(): AIConversation | undefined {
    if (!this.activeConversationId) return undefined;
    return this.conversations.get(this.activeConversationId);
  }

  /**
   * Send a message and get a response.
   */
  async sendMessage(content: string, context?: AIMessageContext): Promise<AIResponse> {
    const conversation = this.getActiveConversation() || this.createConversation();

    // Add user message
    const userMessage: AIMessage = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      content,
      timestamp: Date.now(),
      context: context || this.context,
    };

    conversation.messages.push(userMessage);
    conversation.updatedAt = Date.now();
    this.emit("message-sent", userMessage);

    // Track command
    this.commandHistory.push(content);
    if (this.commandHistory.length > this.maxHistory) {
      this.commandHistory = this.commandHistory.slice(-this.maxHistory);
    }

    // Generate response (simulated AI)
    this.isTyping = true;
    this.emit("typing-started");

    const response = await this.generateResponse(content, conversation);

    this.isTyping = false;
    this.emit("typing-stopped");

    // Add assistant message
    conversation.messages.push(response.message);
    conversation.updatedAt = Date.now();
    this.emit("message-received", response.message);

    return response;
  }

  /**
   * Generate a simulated AI response.
   */
  private async generateResponse(
    input: string,
    conversation: AIConversation
  ): Promise<AIResponse> {
    // Simulate processing delay
    await new Promise((resolve) => setTimeout(resolve, 100 + Math.random() * 200));

    const lowerInput = input.toLowerCase();
    const suggestions: AISuggestion[] = [];
    const actions: AIAction[] = [];
    let responseText = "";

    // Pattern matching for responses
    if (lowerInput.includes("help") || lowerInput.includes("what can you do")) {
      responseText = this.getHelpResponse();
      suggestions.push(
        { id: "s1", type: "action", label: "Open Settings", description: "Configure AI assistant", confidence: 0.9 },
        { id: "s2", type: "info", label: "View History", description: "See past conversations", confidence: 0.8 }
      );
    } else if (lowerInput.includes("open") || lowerInput.includes("show")) {
      const target = this.extractTarget(input);
      responseText = `I'll help you open ${target}.`;
      actions.push({ type: "open-file", target });
      suggestions.push(
        { id: "s1", type: "action", label: `Open ${target}`, description: `Navigate to ${target}`, confidence: 0.95 }
      );
    } else if (lowerInput.includes("search") || lowerInput.includes("find")) {
      const query = this.extractQuery(input);
      responseText = `Searching for "${query}"...`;
      actions.push({ type: "search", target: query });
      suggestions.push(
        { id: "s1", type: "command", label: `Search: ${query}`, description: `Find "${query}" in workspace`, confidence: 0.9 }
      );
    } else if (lowerInput.includes("settings") || lowerInput.includes("preferences")) {
      responseText = "Opening settings for you.";
      actions.push({ type: "navigate", target: "settings" });
      suggestions.push(
        { id: "s1", type: "navigation", label: "Open Settings", description: "View app settings", confidence: 0.95 }
      );
    } else if (lowerInput.includes("memory") || lowerInput.includes("remember")) {
      responseText = "I can help you with memory features. What would you like to remember?";
      suggestions.push(
        { id: "s1", type: "action", label: "Open Memory Explorer", description: "View stored memories", confidence: 0.9 },
        { id: "s2", type: "command", label: "Add Memory", description: "Store a new memory", confidence: 0.85 }
      );
    } else if (lowerInput.includes("workspace")) {
      responseText = "Let me help you with your workspace.";
      suggestions.push(
        { id: "s1", type: "navigation", label: "Open Workspace", description: "View workspace overview", confidence: 0.9 },
        { id: "s2", type: "action", label: "Create Workspace", description: "Start a new workspace", confidence: 0.85 }
      );
    } else if (lowerInput.includes("plugin")) {
      responseText = "Managing plugins for you.";
      suggestions.push(
        { id: "s1", type: "action", label: "View Plugins", description: "See installed plugins", confidence: 0.9 },
        { id: "s2", type: "action", label: "Install Plugin", description: "Browse plugin marketplace", confidence: 0.85 }
      );
    } else {
      // Generic response
      responseText = this.getGenericResponse(input);
      suggestions.push(
        { id: "s1", type: "action", label: "Learn More", description: "Get more information", confidence: 0.7 },
        { id: "s2", type: "command", label: "Try Again", description: "Rephrase your request", confidence: 0.6 }
      );
    }

    const message: AIMessage = {
      id: `msg-${Date.now()}-assistant`,
      role: "assistant",
      content: responseText,
      timestamp: Date.now(),
      suggestions,
    };

    return { message, suggestions, actions };
  }

  /**
   * Get a help response.
   */
  private getHelpResponse(): string {
    return `I'm your AI assistant! Here's what I can help with:

• **Navigation** — "open settings", "show workspace"
• **Search** — "find conversation", "search for X"
• **Memory** — "remember this", "what did I save"
• **Plugins** — "manage plugins", "install plugin"
• **Workspace** — "open workspace", "create workspace"
• **General** — Ask me anything about your AIOS experience!

Just type naturally and I'll do my best to help.`;
  }

  /**
   * Get a generic response.
   */
  private getGenericResponse(input: string): string {
    const responses = [
      `I understand you're asking about "${input}". Let me help with that.`,
      `Interesting question! Here's what I think about "${input}".`,
      `Thanks for asking. Regarding "${input}" — I'm here to help.`,
      `I'm processing your request about "${input}". What specific aspect would you like to explore?`,
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  }

  /**
   * Extract a target from input.
   */
  private extractTarget(input: string): string {
    const words = input.split(" ");
    const openIndex = words.findIndex(
      (w) => w.toLowerCase() === "open" || w.toLowerCase() === "show"
    );
    if (openIndex >= 0 && openIndex < words.length - 1) {
      return words.slice(openIndex + 1).join(" ");
    }
    return "that";
  }

  /**
   * Extract a search query from input.
   */
  private extractQuery(input: string): string {
    const words = input.split(" ");
    const searchIndex = words.findIndex(
      (w) => w.toLowerCase() === "search" || w.toLowerCase() === "find"
    );
    if (searchIndex >= 0 && searchIndex < words.length - 1) {
      const skipWords = ["for", "about", "the", "a", "an"];
      const queryWords = words.slice(searchIndex + 1).filter(
        (w) => !skipWords.includes(w.toLowerCase())
      );
      return queryWords.join(" ") || "everything";
    }
    return "everything";
  }

  /**
   * Update the current context.
   */
  updateContext(context: Partial<AIMessageContext>): void {
    this.context = { ...this.context, ...context };
    this.emit("context-updated", this.context);
  }

  /**
   * Get the current context.
   */
  getContext(): AIMessageContext {
    return { ...this.context };
  }

  /**
   * Get command history.
   */
  getCommandHistory(): string[] {
    return [...this.commandHistory];
  }

  /**
   * Delete a conversation.
   */
  deleteConversation(id: string): boolean {
    const conversation = this.conversations.get(id);
    if (!conversation) return false;

    this.conversations.delete(id);
    if (this.activeConversationId === id) {
      this.activeConversationId = null;
    }
    this.emit("conversation-deleted", id);
    return true;
  }

  /**
   * Get assistant state.
   */
  getState(): AIAssistantState {
    return {
      conversations: this.getConversations(),
      activeConversation: this.activeConversationId,
      isTyping: this.isTyping,
      lastResponse: this.getActiveConversation()?.messages.slice(-1)[0] || null,
    };
  }

  /**
   * Destroy the AI assistant.
   */
  destroy(): void {
    this.conversations.clear();
    this.activeConversationId = null;
    this.commandHistory = [];
    this.context = {};
  }
}

export default AIAssistant;
