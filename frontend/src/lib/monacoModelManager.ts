/**
 * Monaco Editor Model Manager
 * 
 * Optimizes Monaco Editor performance by:
 * - Reusing models instead of recreating them
 * - Managing model lifecycle and memory
 * - Batching model operations
 * - Providing fast model switching
 */

import * as monaco from 'monaco-editor';

interface ManagedModel {
  model: monaco.editor.ITextModel;
  filePath: string;
  language: string;
  lastAccessed: Date;
  isDirty: boolean;
  originalContent: string;
}

interface ModelStats {
  totalModels: number;
  memoryUsage: number;
  oldestModel: Date | null;
  newestModel: Date | null;
}

class MonacoModelManager {
  private models = new Map<string, ManagedModel>();
  private currentModelKey: string | null = null;
  private editor: monaco.editor.IStandaloneCodeEditor | null = null;

  // Configuration
  private readonly MAX_MODELS = 20; // Maximum number of models to keep in memory
  private readonly MODEL_CLEANUP_INTERVAL = 5 * 60 * 1000; // 5 minutes
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.startCleanupTimer();
  }

  /**
   * Set the Monaco editor instance
   */
  setEditor(editor: monaco.editor.IStandaloneCodeEditor): void {
    this.editor = editor;
  }

  /**
   * Get or create a model for the given file
   */
  getOrCreateModel(
    containerId: string,
    filePath: string,
    content: string,
    language: string
  ): monaco.editor.ITextModel {
    const key = this.getModelKey(containerId, filePath);
    const existing = this.models.get(key);

    if (existing) {
      // Update access time
      existing.lastAccessed = new Date();
      
      // Update content if different
      if (existing.model.getValue() !== content) {
        existing.model.setValue(content);
        existing.originalContent = content;
        existing.isDirty = false;
      }

      // Update language if different
      if (existing.language !== language) {
        monaco.editor.setModelLanguage(existing.model, language);
        existing.language = language;
      }

      return existing.model;
    }

    // Create new model
    const uri = monaco.Uri.parse(`file:///${containerId}/${filePath}`);
    const model = monaco.editor.createModel(content, language, uri);

    const managedModel: ManagedModel = {
      model,
      filePath,
      language,
      lastAccessed: new Date(),
      isDirty: false,
      originalContent: content
    };

    this.models.set(key, managedModel);

    // Set up change detection
    model.onDidChangeContent(() => {
      const managed = this.models.get(key);
      if (managed) {
        managed.isDirty = model.getValue() !== managed.originalContent;
      }
    });

    // Enforce model limits
    this.enforceModelLimits();

    return model;
  }

  /**
   * Switch to a model (optimized switching)
   */
  switchToModel(
    containerId: string,
    filePath: string,
    content: string,
    language: string
  ): monaco.editor.ITextModel {
    if (!this.editor) {
      throw new Error('Editor not set. Call setEditor() first.');
    }

    const key = this.getModelKey(containerId, filePath);
    
    // Check if we're already on this model
    if (this.currentModelKey === key) {
      const existing = this.models.get(key);
      if (existing) {
        // Just update content if needed
        if (existing.model.getValue() !== content) {
          existing.model.setValue(content);
          existing.originalContent = content;
          existing.isDirty = false;
        }
        existing.lastAccessed = new Date();
        return existing.model;
      }
    }

    // Get or create the model
    const model = this.getOrCreateModel(containerId, filePath, content, language);

    // Batch the model switch operation
    this.batchModelSwitch(model, key);

    return model;
  }

  /**
   * Batch model switch operations for better performance
   */
  private batchModelSwitch(model: monaco.editor.ITextModel, key: string): void {
    if (!this.editor) return;

    // Use editor.setModel() which is optimized for model switching
    this.editor.setModel(model);
    this.currentModelKey = key;

    // Batch additional operations in next frame
    requestAnimationFrame(() => {
      if (!this.editor) return;

      // Restore cursor position if available
      const savedPosition = this.getSavedCursorPosition(key);
      if (savedPosition) {
        this.editor.setPosition(savedPosition);
      }

      // Restore selection if available
      const savedSelection = this.getSavedSelection(key);
      if (savedSelection) {
        this.editor.setSelection(savedSelection);
      }

      // Focus the editor
      this.editor.focus();
    });
  }

  /**
   * Save current editor state (cursor position, selection, etc.)
   */
  saveEditorState(): void {
    if (!this.editor || !this.currentModelKey) return;

    const position = this.editor.getPosition();
    const selection = this.editor.getSelection();

    if (position) {
      this.saveCursorPosition(this.currentModelKey, position);
    }

    if (selection) {
      this.saveSelection(this.currentModelKey, selection);
    }
  }

  /**
   * Get model by key
   */
  getModel(containerId: string, filePath: string): monaco.editor.ITextModel | null {
    const key = this.getModelKey(containerId, filePath);
    return this.models.get(key)?.model || null;
  }

  /**
   * Check if model exists
   */
  hasModel(containerId: string, filePath: string): boolean {
    const key = this.getModelKey(containerId, filePath);
    return this.models.has(key);
  }

  /**
   * Get all models for a container
   */
  getContainerModels(containerId: string): ManagedModel[] {
    const containerModels: ManagedModel[] = [];
    
    for (const [key, model] of this.models.entries()) {
      if (key.startsWith(`${containerId}:`)) {
        containerModels.push(model);
      }
    }

    return containerModels;
  }

  /**
   * Remove model
   */
  removeModel(containerId: string, filePath: string): boolean {
    const key = this.getModelKey(containerId, filePath);
    const managed = this.models.get(key);

    if (managed) {
      // Save state before disposing
      if (this.currentModelKey === key) {
        this.saveEditorState();
        this.currentModelKey = null;
      }

      // Dispose the model
      managed.model.dispose();
      this.models.delete(key);
      
      // Clear saved state
      this.clearSavedState(key);

      return true;
    }

    return false;
  }

  /**
   * Remove all models for a container
   */
  removeContainerModels(containerId: string): void {
    const keysToRemove: string[] = [];

    for (const key of this.models.keys()) {
      if (key.startsWith(`${containerId}:`)) {
        keysToRemove.push(key);
      }
    }

    keysToRemove.forEach(key => {
      const managed = this.models.get(key);
      if (managed) {
        managed.model.dispose();
        this.models.delete(key);
        this.clearSavedState(key);
      }
    });

    // Clear current model if it belonged to this container
    if (this.currentModelKey && this.currentModelKey.startsWith(`${containerId}:`)) {
      this.currentModelKey = null;
    }
  }

  /**
   * Get statistics about managed models
   */
  getStats(): ModelStats {
    let memoryUsage = 0;
    let oldestModel: Date | null = null;
    let newestModel: Date | null = null;

    for (const managed of this.models.values()) {
      // Estimate memory usage (rough calculation)
      memoryUsage += managed.model.getValue().length * 2; // 2 bytes per character (UTF-16)

      if (!oldestModel || managed.lastAccessed < oldestModel) {
        oldestModel = managed.lastAccessed;
      }

      if (!newestModel || managed.lastAccessed > newestModel) {
        newestModel = managed.lastAccessed;
      }
    }

    return {
      totalModels: this.models.size,
      memoryUsage,
      oldestModel,
      newestModel
    };
  }

  /**
   * Get dirty models (models with unsaved changes)
   */
  getDirtyModels(): Array<{ containerId: string; filePath: string; model: ManagedModel }> {
    const dirty: Array<{ containerId: string; filePath: string; model: ManagedModel }> = [];

    for (const [key, model] of this.models.entries()) {
      if (model.isDirty) {
        const [containerId, ...pathParts] = key.split(':');
        const filePath = pathParts.join(':');
        dirty.push({ containerId, filePath, model });
      }
    }

    return dirty;
  }

  /**
   * Mark model as saved
   */
  markModelSaved(containerId: string, filePath: string): void {
    const key = this.getModelKey(containerId, filePath);
    const managed = this.models.get(key);

    if (managed) {
      // Defer the potentially expensive getValue() call to avoid blocking
      setTimeout(() => {
        managed.originalContent = managed.model.getValue();
        managed.isDirty = false;
      }, 0);
    }
  }

  /**
   * Dispose all models and cleanup
   */
  dispose(): void {
    // Save current editor state
    this.saveEditorState();

    // Dispose all models
    for (const managed of this.models.values()) {
      managed.model.dispose();
    }

    this.models.clear();
    this.currentModelKey = null;

    // Clear cleanup timer
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }

    // Clear saved states
    this.clearAllSavedStates();
  }

  // Private methods

  private getModelKey(containerId: string, filePath: string): string {
    return `${containerId}:${filePath}`;
  }

  private enforceModelLimits(): void {
    if (this.models.size <= this.MAX_MODELS) return;

    // Sort models by last accessed time (oldest first)
    const sortedModels = Array.from(this.models.entries())
      .sort(([, a], [, b]) => a.lastAccessed.getTime() - b.lastAccessed.getTime());

    // Remove oldest models until we're under the limit
    const toRemove = sortedModels.slice(0, this.models.size - this.MAX_MODELS);

    for (const [key, managed] of toRemove) {
      // Don't remove the current model
      if (key === this.currentModelKey) continue;

      managed.model.dispose();
      this.models.delete(key);
      this.clearSavedState(key);
    }
  }

  private startCleanupTimer(): void {
    this.cleanupTimer = setInterval(() => {
      this.cleanupOldModels();
    }, this.MODEL_CLEANUP_INTERVAL);
  }

  private cleanupOldModels(): void {
    const now = new Date();
    const cutoffTime = new Date(now.getTime() - 30 * 60 * 1000); // 30 minutes ago

    const keysToRemove: string[] = [];

    for (const [key, managed] of this.models.entries()) {
      // Don't cleanup current model or dirty models
      if (key === this.currentModelKey || managed.isDirty) continue;

      if (managed.lastAccessed < cutoffTime) {
        keysToRemove.push(key);
      }
    }

    keysToRemove.forEach(key => {
      const managed = this.models.get(key);
      if (managed) {
        managed.model.dispose();
        this.models.delete(key);
        this.clearSavedState(key);
      }
    });

    if (keysToRemove.length > 0) {
      console.log(`Monaco: Cleaned up ${keysToRemove.length} old models`);
    }
  }

  // Cursor position and selection management
  private cursorPositions = new Map<string, monaco.Position>();
  private selections = new Map<string, monaco.Selection>();

  private saveCursorPosition(key: string, position: monaco.Position): void {
    this.cursorPositions.set(key, position);
  }

  private getSavedCursorPosition(key: string): monaco.Position | null {
    return this.cursorPositions.get(key) || null;
  }

  private saveSelection(key: string, selection: monaco.Selection): void {
    this.selections.set(key, selection);
  }

  private getSavedSelection(key: string): monaco.Selection | null {
    return this.selections.get(key) || null;
  }

  private clearSavedState(key: string): void {
    this.cursorPositions.delete(key);
    this.selections.delete(key);
  }

  private clearAllSavedStates(): void {
    this.cursorPositions.clear();
    this.selections.clear();
  }
}

// Global model manager instance
export const monacoModelManager = new MonacoModelManager();

// Export types for use in components
export type { ManagedModel, ModelStats };