import { log } from "../vite";
import { metrics } from "../services/monitoringService";
import { db } from "@db";

interface SystemMetrics {
  memory: {
    heapUsed: number;
    heapTotal: number;
    rss: number;
    external: number;
  };
  cpu: {
    user: number;
    system: number;
  };
  uptime: number;
  bookmarks?: {
    total: number;
    pendingAnalysis: number;
    failedAnalysis: number;
  };
  aiProcessing?: {
    activeRequests: number;
    averageProcessingTime: number;
    errorRate: number;
  };
  database?: {
    activeConnections: number;
    idleConnections: number;
    waitingRequests: number;
  };
}

class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metricsHistory: SystemMetrics[] = [];
  private readonly maxHistorySize = 100;
  private lastCpuUsage = process.cpuUsage();
  private lastCheck = Date.now();
  private aiMetrics = {
    requestCount: 0,
    errorCount: 0,
    totalProcessingTime: 0,
  };

  private constructor() {
    this.startMonitoring();
  }

  public static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  private startMonitoring() {
    // Collect metrics every minute
    setInterval(() => {
      this.collectMetrics();
    }, 60000);
  }

  public trackAIRequest(duration: number, success: boolean) {
    this.aiMetrics.requestCount++;
    if (!success) this.aiMetrics.errorCount++;
    this.aiMetrics.totalProcessingTime += duration;

    // Update Prometheus metrics
    metrics.aiProcessingDuration.observe(duration);
  }

  private async collectDatabaseMetrics() {
    try {
      const result = await db.execute(sql`SELECT count(*) as count FROM pg_stat_activity`);
      return {
        activeConnections: result[0]?.count || 0,
        idleConnections: 0, // Will be implemented when we have access to pool metrics
        waitingRequests: 0,
      };
    } catch (error) {
      console.error("Failed to collect database metrics:", error);
      return null;
    }
  }

  private async collectBookmarkMetrics() {
    try {
      const [total, pending, failed] = await Promise.all([
        db.execute(sql`SELECT COUNT(*) as count FROM bookmarks`),
        db.execute(sql`SELECT COUNT(*) as count FROM bookmarks WHERE analysis->>'status' = 'processing'`),
        db.execute(sql`SELECT COUNT(*) as count FROM bookmarks WHERE analysis->>'status' = 'error'`)
      ]);

      return {
        total: total[0]?.count || 0,
        pendingAnalysis: pending[0]?.count || 0,
        failedAnalysis: failed[0]?.count || 0,
      };
    } catch (error) {
      console.error("Failed to collect bookmark metrics:", error);
      return null;
    }
  }

  private async collectMetrics() {
    const currentTime = Date.now();
    const currentCpuUsage = process.cpuUsage();
    const cpuDiff = {
      user: currentCpuUsage.user - this.lastCpuUsage.user,
      system: currentCpuUsage.system - this.lastCpuUsage.system
    };
    const elapsedMs = currentTime - this.lastCheck;

    // Calculate CPU percentage
    const cpuPercent = {
      user: (cpuDiff.user / 1000 / elapsedMs) * 100,
      system: (cpuDiff.system / 1000 / elapsedMs) * 100
    };

    const memoryMetrics = process.memoryUsage();
    const [bookmarkMetrics, dbMetrics] = await Promise.all([
      this.collectBookmarkMetrics(),
      this.collectDatabaseMetrics()
    ]);

    const metrics: SystemMetrics = {
      memory: {
        heapUsed: memoryMetrics.heapUsed,
        heapTotal: memoryMetrics.heapTotal,
        rss: memoryMetrics.rss,
        external: memoryMetrics.external
      },
      cpu: cpuPercent,
      uptime: process.uptime(),
      bookmarks: bookmarkMetrics || undefined,
      database: dbMetrics || undefined,
      aiProcessing: this.aiMetrics.requestCount ? {
        activeRequests: this.aiMetrics.requestCount,
        averageProcessingTime: this.aiMetrics.totalProcessingTime / this.aiMetrics.requestCount,
        errorRate: this.aiMetrics.errorCount / this.aiMetrics.requestCount
      } : undefined
    };

    this.metricsHistory.push(metrics);
    if (this.metricsHistory.length > this.maxHistorySize) {
      this.metricsHistory.shift();
    }

    // Log critical metrics
    const heapUsedMB = Math.round(metrics.memory.heapUsed / 1024 / 1024);
    const heapTotalMB = Math.round(metrics.memory.heapTotal / 1024 / 1024);
    const rssMB = Math.round(metrics.memory.rss / 1024 / 1024);

    if (heapUsedMB > heapTotalMB * 0.8) {
      log(`[WARNING] High memory usage: ${heapUsedMB}MB / ${heapTotalMB}MB`, 'monitor');
    }

    if (cpuPercent.user + cpuPercent.system > 80) {
      log(`[WARNING] High CPU usage: ${Math.round(cpuPercent.user + cpuPercent.system)}%`, 'monitor');
    }

    // Reset AI metrics after collection
    this.aiMetrics = {
      requestCount: 0,
      errorCount: 0,
      totalProcessingTime: 0,
    };

    log(`[Metrics] Memory: ${heapUsedMB}MB/${heapTotalMB}MB (RSS: ${rssMB}MB) CPU: ${Math.round(cpuPercent.user + cpuPercent.system)}%`, 'monitor');

    if (bookmarkMetrics) {
      log(`[Metrics] Bookmarks: Total=${bookmarkMetrics.total}, Pending=${bookmarkMetrics.pendingAnalysis}, Failed=${bookmarkMetrics.failedAnalysis}`, 'monitor');
    }
  }

  public getLatestMetrics(): SystemMetrics | null {
    return this.metricsHistory[this.metricsHistory.length - 1] || null;
  }

  public getMetricsHistory(): SystemMetrics[] {
    return [...this.metricsHistory];
  }

  public resetMetrics() {
    this.metricsHistory = [];
    this.lastCpuUsage = process.cpuUsage();
    this.lastCheck = Date.now();
    this.aiMetrics = {
      requestCount: 0,
      errorCount: 0,
      totalProcessingTime: 0,
    };
  }
}

export const performanceMonitor = PerformanceMonitor.getInstance();