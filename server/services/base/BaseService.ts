import { injectable } from 'tsyringe';
import { logger } from '../../utils/logger';

@injectable()
export abstract class BaseService {
    protected async executeOperation<T>(
        operation: string,
        func: () => Promise<T>
    ): Promise<T> {
        const startTime = Date.now();
        try {
            const result = await func();
            this.logOperation(operation, Date.now() - startTime);
            return result;
        } catch (error) {
            this.logOperation(operation, Date.now() - startTime, true);
            this.handleError(error as Error);
            throw error;
        }
    }

    protected logOperation(operation: string, duration: number, error: boolean = false): void {
        if (error) {
            logger.error(`Operation failed: ${operation}`, { duration });
        } else {
            logger.info(`Operation completed: ${operation}`, { duration });
        }
    }

    protected handleError(error: Error): void {
        logger.error('Service error:', {
            message: error.message,
            name: error.name
        });
    }
} 