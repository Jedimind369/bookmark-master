import axios from 'axios';
import { logger } from '../utils/logger';

/**
 * Service for interacting with the Python processor microservice
 */
export class ProcessorService {
  private baseUrl: string;
  
  /**
   * Creates a new ProcessorService instance
   * @param baseUrl The base URL of the processor service
   */
  constructor(baseUrl: string = process.env.PROCESSOR_URL || 'http://processor:5000') {
    this.baseUrl = baseUrl;
    logger.info(`ProcessorService initialized with baseUrl: ${this.baseUrl}`);
  }
  
  /**
   * Checks if the processor service is healthy
   * @returns Promise resolving to true if healthy, false otherwise
   */
  async isHealthy(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.baseUrl}/health`);
      return response.status === 200 && response.data.status === 'ok';
    } catch (error) {
      logger.error('Health check failed for processor service', { error });
      return false;
    }
  }
  
  /**
   * Processes a JSON file containing bookmarks
   * @param filePath Path to the JSON file
   * @param options Processing options
   * @returns Promise resolving to the processing result
   */
  async processJsonFile(filePath: string, options: ProcessingOptions = {}): Promise<ProcessingResult> {
    try {
      const startTime = Date.now();
      logger.info(`Starting JSON file processing: ${filePath}`);
      
      const response = await axios.post(`${this.baseUrl}/process/json`, {
        file_path: filePath,
        max_workers: options.maxWorkers,
        min_chunk_size: options.minChunkSize,
        max_chunk_size: options.maxChunkSize,
        memory_target: options.memoryTarget
      });
      
      const duration = Date.now() - startTime;
      logger.info(`Completed JSON file processing in ${duration}ms`, { 
        filePath, 
        duration,
        itemsProcessed: response.data.items_processed 
      });
      
      return {
        success: true,
        itemsProcessed: response.data.items_processed,
        duration: duration,
        outputPath: response.data.output_path
      };
    } catch (error) {
      logger.error('Error processing JSON file', { filePath, error });
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
  
  /**
   * Processes a list of URLs
   * @param urls Array of URLs to process
   * @param options Processing options
   * @returns Promise resolving to the processing result
   */
  async processUrls(urls: string[], options: ProcessingOptions = {}): Promise<ProcessingResult> {
    try {
      const startTime = Date.now();
      logger.info(`Starting URL list processing with ${urls.length} URLs`);
      
      const response = await axios.post(`${this.baseUrl}/process/urls`, {
        urls: urls,
        max_workers: options.maxWorkers,
        min_chunk_size: options.minChunkSize,
        max_chunk_size: options.maxChunkSize,
        memory_target: options.memoryTarget
      });
      
      const duration = Date.now() - startTime;
      logger.info(`Completed URL list processing in ${duration}ms`, { 
        urlCount: urls.length, 
        duration,
        itemsProcessed: response.data.items_processed 
      });
      
      return {
        success: true,
        itemsProcessed: response.data.items_processed,
        duration: duration,
        outputPath: response.data.output_path
      };
    } catch (error) {
      logger.error('Error processing URL list', { urlCount: urls.length, error });
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
  
  /**
   * Generates an HTML report from processed bookmarks
   * @param inputPath Path to the processed bookmarks file
   * @param options Report generation options
   * @returns Promise resolving to the report generation result
   */
  async generateReport(inputPath: string, options: ReportOptions = {}): Promise<ReportResult> {
    try {
      const startTime = Date.now();
      logger.info(`Starting report generation for: ${inputPath}`);
      
      const response = await axios.post(`${this.baseUrl}/report`, {
        input_path: inputPath,
        output_path: options.outputPath,
        template: options.template,
        max_workers: options.maxWorkers
      });
      
      const duration = Date.now() - startTime;
      logger.info(`Completed report generation in ${duration}ms`, { 
        inputPath, 
        duration,
        outputPath: response.data.output_path 
      });
      
      return {
        success: true,
        duration: duration,
        outputPath: response.data.output_path
      };
    } catch (error) {
      logger.error('Error generating report', { inputPath, error });
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
  
  /**
   * Gets statistics about the processor service
   * @returns Promise resolving to processor statistics
   */
  async getStats(): Promise<ProcessorStats> {
    try {
      const response = await axios.get(`${this.baseUrl}/stats`);
      return response.data;
    } catch (error) {
      logger.error('Error fetching processor stats', { error });
      throw error;
    }
  }
}

/**
 * Options for processing operations
 */
export interface ProcessingOptions {
  maxWorkers?: number;
  minChunkSize?: number;
  maxChunkSize?: number;
  memoryTarget?: number;
}

/**
 * Result of a processing operation
 */
export interface ProcessingResult {
  success: boolean;
  itemsProcessed?: number;
  duration?: number;
  outputPath?: string;
  error?: string;
}

/**
 * Options for report generation
 */
export interface ReportOptions {
  outputPath?: string;
  template?: string;
  maxWorkers?: number;
}

/**
 * Result of a report generation operation
 */
export interface ReportResult {
  success: boolean;
  duration?: number;
  outputPath?: string;
  error?: string;
}

/**
 * Statistics about the processor service
 */
export interface ProcessorStats {
  activeWorkers: number;
  memoryUsageBytes: number;
  requestsProcessed: number;
  errorsTotal: number;
  averageProcessingTime: number;
  uptime: number;
}

// Export a singleton instance
export const processorService = new ProcessorService(); 