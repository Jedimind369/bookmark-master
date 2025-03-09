/**
 * Simple logger utility for the application
 */
export const logger = {
  /**
   * Logs an informational message
   * @param message The message to log
   * @param meta Optional metadata to include
   */
  info(message: string, meta?: Record<string, any>): void {
    console.log(`[INFO] ${message}`, meta ? meta : '');
  },
  
  /**
   * Logs a warning message
   * @param message The message to log
   * @param meta Optional metadata to include
   */
  warn(message: string, meta?: Record<string, any>): void {
    console.warn(`[WARN] ${message}`, meta ? meta : '');
  },
  
  /**
   * Logs an error message
   * @param message The message to log
   * @param meta Optional metadata to include
   */
  error(message: string, meta?: Record<string, any>): void {
    console.error(`[ERROR] ${message}`, meta ? meta : '');
  },
  
  /**
   * Logs a debug message
   * @param message The message to log
   * @param meta Optional metadata to include
   */
  debug(message: string, meta?: Record<string, any>): void {
    if (process.env.NODE_ENV !== 'production') {
      console.debug(`[DEBUG] ${message}`, meta ? meta : '');
    }
  }
}; 