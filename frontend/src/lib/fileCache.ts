/**
 * Intelligent File Caching System for Performance Optimization
 * 
 * Features:
 * - LRU cache with size limits
 * - TTL-based expiration
 * - Cache invalidation on file changes
 * - Memory usage monitoring
 * - Preloading support
 */

interface CachedFile {
  content: string;
  language: string;
  size: number;
  lastModified: Date;
  lastAccessed: Date;
  ttl: number; // Time to live in ms
}

interface CacheStats {
  hits: number;
  misses: number;
  evictions: number;
  totalSize: number;
  itemCount: number;
}

class FileCache {
  private cache = new Map<string, CachedFile>();
  private accessOrder: string[] = []; // For LRU implementation
  private stats: CacheStats = {
    hits: 0,
    misses: 0,
    evictions: 0,
    totalSize: 0,
    itemCount: 0
  };

  // Configuration
  private readonly MAX_CACHE_SIZE = 50 * 1024 * 1024; // 50MB
  private readonly MAX_ITEMS = 100;
  private readonly DEFAULT_TTL = 10 * 60 * 1000; // 10 minutes
  private readonly LARGE_FILE_THRESHOLD = 1024 * 1024; // 1MB

  /**
   * Get file from cache or return null if not cached/expired
   */
  get(containerId: string, filePath: string): CachedFile | null {
    const key = this.getCacheKey(containerId, filePath);
    const cached = this.cache.get(key);

    if (!cached) {
      this.stats.misses++;
      return null;
    }

    // Check TTL expiration
    const now = Date.now();
    if (now - cached.lastAccessed.getTime() > cached.ttl) {
      this.delete(containerId, filePath);
      this.stats.misses++;
      return null;
    }

    // Update access time and LRU order
    cached.lastAccessed = new Date();
    this.updateAccessOrder(key);
    this.stats.hits++;

    return cached;
  }

  /**
   * Store file in cache with intelligent TTL based on file size
   */
  set(
    containerId: string, 
    filePath: string, 
    content: string, 
    language: string,
    customTTL?: number
  ): void {
    const key = this.getCacheKey(containerId, filePath);
    
    // Use faster size calculation to avoid blocking
    const size = content.length * 2; // Rough estimate: 2 bytes per character for UTF-16
    
    // Calculate dynamic TTL based on file size and access patterns
    let ttl = customTTL || this.calculateTTL(size, filePath);

    const cachedFile: CachedFile = {
      content,
      language,
      size,
      lastModified: new Date(),
      lastAccessed: new Date(),
      ttl
    };

    // Remove existing entry if it exists
    if (this.cache.has(key)) {
      this.stats.totalSize -= this.cache.get(key)!.size;
    } else {
      this.stats.itemCount++;
    }

    // Add new entry
    this.cache.set(key, cachedFile);
    this.stats.totalSize += size;
    this.updateAccessOrder(key);

    // Defer cache limit enforcement to avoid blocking
    setTimeout(() => {
      this.enforceLimits();
    }, 0);
  }

  /**
   * Delete specific file from cache
   */
  delete(containerId: string, filePath: string): boolean {
    const key = this.getCacheKey(containerId, filePath);
    const cached = this.cache.get(key);
    
    if (cached) {
      this.cache.delete(key);
      this.stats.totalSize -= cached.size;
      this.stats.itemCount--;
      this.removeFromAccessOrder(key);
      return true;
    }
    
    return false;
  }

  /**
   * Invalidate all files for a container (e.g., when container changes)
   */
  invalidateContainer(containerId: string): void {
    const keysToDelete: string[] = [];
    
    for (const key of this.cache.keys()) {
      if (key.startsWith(`${containerId}:`)) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach(key => {
      const cached = this.cache.get(key);
      if (cached) {
        this.cache.delete(key);
        this.stats.totalSize -= cached.size;
        this.stats.itemCount--;
        this.removeFromAccessOrder(key);
      }
    });
  }

  /**
   * Check if file is cached and not expired
   */
  has(containerId: string, filePath: string): boolean {
    return this.get(containerId, filePath) !== null;
  }

  /**
   * Get cache statistics for monitoring
   */
  getStats(): CacheStats & { hitRate: number; memoryUsage: string } {
    const totalRequests = this.stats.hits + this.stats.misses;
    const hitRate = totalRequests > 0 ? (this.stats.hits / totalRequests) * 100 : 0;
    
    return {
      ...this.stats,
      hitRate: Math.round(hitRate * 100) / 100,
      memoryUsage: this.formatBytes(this.stats.totalSize)
    };
  }

  /**
   * Clear entire cache
   */
  clear(): void {
    this.cache.clear();
    this.accessOrder = [];
    this.stats = {
      hits: 0,
      misses: 0,
      evictions: 0,
      totalSize: 0,
      itemCount: 0
    };
  }

  /**
   * Get list of cached file paths for a container
   */
  getCachedFiles(containerId: string): string[] {
    const files: string[] = [];
    
    for (const key of this.cache.keys()) {
      if (key.startsWith(`${containerId}:`)) {
        files.push(key.substring(containerId.length + 1));
      }
    }
    
    return files;
  }

  // Private methods

  private getCacheKey(containerId: string, filePath: string): string {
    return `${containerId}:${filePath}`;
  }

  private calculateTTL(fileSize: number, filePath: string): number {
    // Larger files get shorter TTL to prevent memory bloat
    if (fileSize > this.LARGE_FILE_THRESHOLD) {
      return 5 * 60 * 1000; // 5 minutes for large files
    }

    // Frequently accessed file types get longer TTL
    const extension = filePath.split('.').pop()?.toLowerCase();
    const importantExtensions = ['py', 'js', 'ts', 'json', 'md'];
    
    if (importantExtensions.includes(extension || '')) {
      return 15 * 60 * 1000; // 15 minutes for important files
    }

    return this.DEFAULT_TTL;
  }

  private updateAccessOrder(key: string): void {
    // Remove from current position
    this.removeFromAccessOrder(key);
    // Add to end (most recently used)
    this.accessOrder.push(key);
  }

  private removeFromAccessOrder(key: string): void {
    const index = this.accessOrder.indexOf(key);
    if (index > -1) {
      this.accessOrder.splice(index, 1);
    }
  }

  private enforceLimits(): void {
    // Limit the number of evictions per call to prevent blocking
    const MAX_EVICTIONS_PER_CALL = 5;
    let evictions = 0;
    
    // Enforce item count limit (but limit evictions to prevent blocking)
    while (this.stats.itemCount > this.MAX_ITEMS && 
           this.accessOrder.length > 0 && 
           evictions < MAX_EVICTIONS_PER_CALL) {
      this.evictLRU();
      evictions++;
    }

    // Enforce size limit (but limit evictions to prevent blocking)
    while (this.stats.totalSize > this.MAX_CACHE_SIZE && 
           this.accessOrder.length > 0 && 
           evictions < MAX_EVICTIONS_PER_CALL) {
      this.evictLRU();
      evictions++;
    }
    
    // If we still need to evict more, schedule another round
    if ((this.stats.itemCount > this.MAX_ITEMS || this.stats.totalSize > this.MAX_CACHE_SIZE) &&
        this.accessOrder.length > 0) {
      setTimeout(() => {
        this.enforceLimits();
      }, 10); // Small delay before next round
    }
  }

  private evictLRU(): void {
    if (this.accessOrder.length === 0) return;

    const lruKey = this.accessOrder[0];
    const cached = this.cache.get(lruKey);
    
    if (cached) {
      this.cache.delete(lruKey);
      this.stats.totalSize -= cached.size;
      this.stats.itemCount--;
      this.stats.evictions++;
      this.accessOrder.shift();
    }
  }

  private formatBytes(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}

// Global cache instance
export const fileCache = new FileCache();

// Set up initial file cache listener
if (typeof window !== 'undefined') {
  window.addEventListener('initial-file-cache', (event: CustomEvent) => {
    const { containerId, filePath, content, language } = event.detail;
    
    try {
      console.log(`🚀 Pre-caching initial file: ${filePath}`);
      fileCache.set(containerId, filePath, content, language);
      
      // Emit cache event for monitoring
      cacheEvents.emit({
        type: 'set',
        containerId,
        filePath,
        size: content.length,
        stats: fileCache.getStats()
      });
      
    } catch (error) {
      console.error('Failed to pre-cache initial file:', error);
    }
  });
}

// Cache event types for monitoring
export type CacheEvent = 'hit' | 'miss' | 'set' | 'evict' | 'clear';

export interface CacheEventData {
  type: CacheEvent;
  containerId?: string;
  filePath?: string;
  size?: number;
  stats: ReturnType<FileCache['getStats']>;
}

// Optional cache event emitter for debugging/monitoring
class CacheEventEmitter {
  private listeners: ((event: CacheEventData) => void)[] = [];

  subscribe(listener: (event: CacheEventData) => void): () => void {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  emit(event: CacheEventData): void {
    this.listeners.forEach(listener => listener(event));
  }
}

export const cacheEvents = new CacheEventEmitter();