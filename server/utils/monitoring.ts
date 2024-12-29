import { log } from "../vite";

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
}

class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metricsHistory: SystemMetrics[] = [];
  private readonly maxHistorySize = 100;
  private lastCpuUsage = process.cpuUsage();
  private lastCheck = Date.now();

  private constructor() {
    // Initialize monitoring
    this.startMonitoring();
  }

  public static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  private startMonitoring() {
    setInterval(() => {
      this.collectMetrics();
    }, 60000); // Collect metrics every minute
  }

  private collectMetrics() {
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

    const metrics: SystemMetrics = {
      memory: {
        ...process.memoryUsage(),
        heapUsed: process.memoryUsage().heapUsed,
        heapTotal: process.memoryUsage().heapTotal,
        rss: process.memoryUsage().rss,
        external: process.memoryUsage().external
      },
      cpu: cpuPercent,
      uptime: process.uptime()
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

    log(`[Metrics] Memory: ${heapUsedMB}MB/${heapTotalMB}MB (RSS: ${rssMB}MB) CPU: ${Math.round(cpuPercent.user + cpuPercent.system)}%`, 'monitor');
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
  }
}

export const performanceMonitor = PerformanceMonitor.getInstance();
