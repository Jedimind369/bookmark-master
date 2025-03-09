import axios from 'axios';
import { ProcessorService } from '../ProcessorService';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock logger
jest.mock('../../utils/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
  },
}));

describe('ProcessorService', () => {
  let service: ProcessorService;

  beforeEach(() => {
    jest.clearAllMocks();
    service = new ProcessorService('http://test-processor:5000');
  });

  describe('isHealthy', () => {
    it('should return true when health check succeeds', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        status: 200,
        data: { status: 'ok', memory_usage: 1024, uptime: 60 },
      });

      const result = await service.isHealthy();
      expect(result).toBe(true);
      expect(mockedAxios.get).toHaveBeenCalledWith('http://test-processor:5000/health');
    });

    it('should return false when health check fails', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Connection error'));

      const result = await service.isHealthy();
      expect(result).toBe(false);
    });

    it('should return false when status is not ok', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        status: 200,
        data: { status: 'error', memory_usage: 1024, uptime: 60 },
      });

      const result = await service.isHealthy();
      expect(result).toBe(false);
    });
  });

  describe('processJsonFile', () => {
    it('should process a JSON file successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({
        data: {
          items_processed: 100,
          output_path: '/output/processed.json',
        },
      });

      const result = await service.processJsonFile('/input/bookmarks.json', {
        maxWorkers: 4,
        minChunkSize: 100,
        maxChunkSize: 1000,
        memoryTarget: 70,
      });

      expect(result.success).toBe(true);
      expect(result.itemsProcessed).toBe(100);
      expect(result.outputPath).toBe('/output/processed.json');

      expect(mockedAxios.post).toHaveBeenCalledWith('http://test-processor:5000/process/json', {
        file_path: '/input/bookmarks.json',
        max_workers: 4,
        min_chunk_size: 100,
        max_chunk_size: 1000,
        memory_target: 70,
      });
    });

    it('should handle errors when processing a JSON file', async () => {
      mockedAxios.post.mockRejectedValueOnce(new Error('Processing error'));

      const result = await service.processJsonFile('/input/bookmarks.json');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Processing error');
    });
  });

  describe('processUrls', () => {
    it('should process URLs successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({
        data: {
          items_processed: 10,
          output_path: '/output/urls_processed.json',
        },
      });

      const urls = ['https://example.com', 'https://test.com'];
      const result = await service.processUrls(urls, { maxWorkers: 2 });

      expect(result.success).toBe(true);
      expect(result.itemsProcessed).toBe(10);
      expect(result.outputPath).toBe('/output/urls_processed.json');

      expect(mockedAxios.post).toHaveBeenCalledWith('http://test-processor:5000/process/urls', {
        urls: urls,
        max_workers: 2,
        min_chunk_size: undefined,
        max_chunk_size: undefined,
        memory_target: undefined,
      });
    });

    it('should handle errors when processing URLs', async () => {
      mockedAxios.post.mockRejectedValueOnce(new Error('URL processing error'));

      const urls = ['https://example.com'];
      const result = await service.processUrls(urls);

      expect(result.success).toBe(false);
      expect(result.error).toBe('URL processing error');
    });
  });

  describe('generateReport', () => {
    it('should generate a report successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({
        data: {
          output_path: '/output/report.html',
        },
      });

      const result = await service.generateReport('/input/processed.json', {
        outputPath: '/output/custom_report.html',
        template: 'custom',
        maxWorkers: 2,
      });

      expect(result.success).toBe(true);
      expect(result.outputPath).toBe('/output/report.html');

      expect(mockedAxios.post).toHaveBeenCalledWith('http://test-processor:5000/report', {
        input_path: '/input/processed.json',
        output_path: '/output/custom_report.html',
        template: 'custom',
        max_workers: 2,
      });
    });

    it('should handle errors when generating a report', async () => {
      mockedAxios.post.mockRejectedValueOnce(new Error('Report generation error'));

      const result = await service.generateReport('/input/processed.json');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Report generation error');
    });
  });

  describe('getStats', () => {
    it('should get processor statistics successfully', async () => {
      const statsData = {
        activeWorkers: 2,
        memoryUsageBytes: 1024 * 1024,
        requestsProcessed: 100,
        errorsTotal: 5,
        averageProcessingTime: 0.75,
        uptime: 3600,
      };

      mockedAxios.get.mockResolvedValueOnce({
        data: statsData,
      });

      const result = await service.getStats();

      expect(result).toEqual(statsData);
      expect(mockedAxios.get).toHaveBeenCalledWith('http://test-processor:5000/stats');
    });

    it('should throw an error when stats request fails', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Stats error'));

      await expect(service.getStats()).rejects.toThrow('Stats error');
    });
  });
}); 