import { IMetricsService, Metric, PerformanceStats } from '../../interfaces/services';

interface PerformanceMetric {
    count: number;
    totalDuration: number;
    errors: number;
    lastUpdate: number;
}

export class MetricsService implements IMetricsService {
    private metrics = new Map<string, PerformanceMetric>();
    private startTime = Date.now();

    track(metric: Metric): void {
        const existing = this.metrics.get(metric.operation) || {
            count: 0,
            totalDuration: 0,
            errors: 0,
            lastUpdate: Date.now()
        };

        this.metrics.set(metric.operation, {
            count: existing.count + 1,
            totalDuration: existing.totalDuration + (metric.duration || 0),
            errors: existing.errors + (metric.error ? 1 : 0),
            lastUpdate: Date.now()
        });
    }

    getStats(): PerformanceStats {
        let totalRequests = 0;
        let totalDuration = 0;
        let totalErrors = 0;

        this.metrics.forEach(metric => {
            totalRequests += metric.count;
            totalDuration += metric.totalDuration;
            totalErrors += metric.errors;
        });

        return {
            requestCount: totalRequests,
            averageResponseTime: totalRequests > 0 ? totalDuration / totalRequests : 0,
            errorRate: totalRequests > 0 ? totalErrors / totalRequests : 0,
            memoryUsage: process.memoryUsage().heapUsed
        };
    }

    // Additional utility methods
    getMetricsByOperation(operation: string): PerformanceMetric | undefined {
        return this.metrics.get(operation);
    }

    getUptime(): number {
        return Date.now() - this.startTime;
    }

    reset(): void {
        this.metrics.clear();
        this.startTime = Date.now();
    }

    cleanup(maxAge: number = 24 * 60 * 60 * 1000): void {
        const now = Date.now();
        const entries = Array.from(this.metrics.entries());
        entries.forEach(([operation, metric]) => {
            if (now - metric.lastUpdate > maxAge) {
                this.metrics.delete(operation);
            }
        });
    }
} 