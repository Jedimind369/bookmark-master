import { logger } from './logger';

class PerformanceMonitor {
    private metrics = {
        requests: {
            total: 0,
            failed: 0,
            inProgress: 0
        },
        database: {
            operations: 0,
            totalDuration: 0,
            errors: 0
        },
        ai: {
            requests: 0,
            totalDuration: 0,
            errors: 0
        },
        memory: {
            peak: 0,
            current: 0
        }
    };

    private startTime = Date.now();

    trackRequest(duration: number, success: boolean): void {
        this.metrics.requests.total++;
        if (!success) {
            this.metrics.requests.failed++;
        }
        this.updateMemoryUsage();
    }

    trackDatabaseOperation(operation: string, duration: number, error?: Error): void {
        this.metrics.database.operations++;
        this.metrics.database.totalDuration += duration;
        if (error) {
            this.metrics.database.errors++;
            logger.error(`Database operation failed: ${operation}`, { error });
        }
        this.updateMemoryUsage();
    }

    trackAIRequest(duration: number, success: boolean): void {
        this.metrics.ai.requests++;
        this.metrics.ai.totalDuration += duration;
        if (!success) {
            this.metrics.ai.errors++;
        }
        this.updateMemoryUsage();
    }

    private updateMemoryUsage(): void {
        const memoryUsage = process.memoryUsage();
        this.metrics.memory.current = memoryUsage.heapUsed;
        this.metrics.memory.peak = Math.max(this.metrics.memory.peak, memoryUsage.heapUsed);
    }

    getMetrics() {
        return {
            ...this.metrics,
            uptime: Date.now() - this.startTime,
            averages: {
                requestDuration: this.metrics.requests.total > 0
                    ? this.metrics.database.totalDuration / this.metrics.requests.total
                    : 0,
                aiRequestDuration: this.metrics.ai.requests > 0
                    ? this.metrics.ai.totalDuration / this.metrics.ai.requests
                    : 0,
                errorRate: this.metrics.requests.total > 0
                    ? this.metrics.requests.failed / this.metrics.requests.total
                    : 0
            }
        };
    }

    resetMetrics(): void {
        this.metrics = {
            requests: { total: 0, failed: 0, inProgress: 0 },
            database: { operations: 0, totalDuration: 0, errors: 0 },
            ai: { requests: 0, totalDuration: 0, errors: 0 },
            memory: { peak: 0, current: 0 }
        };
        this.startTime = Date.now();
        this.updateMemoryUsage();
    }

    logMetrics(): void {
        const metrics = this.getMetrics();
        logger.info('Performance Metrics:', {
            metrics,
            timestamp: new Date().toISOString()
        });
    }
}

export const performanceMonitor = new PerformanceMonitor();