import express from 'express';
import { container } from '../container';
import type { IBookmarkService } from '../interfaces/services';
import { logger } from '../utils/logger';

const router = express.Router();
const bookmarkService = container.resolve<IBookmarkService>('IBookmarkService');

// Create a new bookmark
router.post('/', async (req, res) => {
    try {
        const bookmark = await bookmarkService.enrich(req.body);
        await bookmarkService.save(bookmark);
        res.status(201).json(bookmark);
    } catch (error) {
        logger.error('Failed to create bookmark:', {
            error: error instanceof Error ? error.message : 'Unknown error',
            body: req.body
        });
        res.status(400).json({
            error: error instanceof Error ? error.message : 'Failed to create bookmark'
        });
    }
});

// Validate a URL
router.post('/validate', async (req, res) => {
    try {
        const { url } = req.body;
        if (!url) {
            return res.status(400).json({ error: 'URL is required' });
        }

        const result = await bookmarkService.validate(url);
        res.json(result);
    } catch (error) {
        logger.error('Failed to validate URL:', {
            error: error instanceof Error ? error.message : 'Unknown error',
            body: req.body
        });
        res.status(400).json({
            error: error instanceof Error ? error.message : 'Failed to validate URL'
        });
    }
});

// Get enriched bookmark data
router.post('/enrich', async (req, res) => {
    try {
        const bookmark = await bookmarkService.enrich(req.body);
        res.json(bookmark);
    } catch (error) {
        logger.error('Failed to enrich bookmark:', {
            error: error instanceof Error ? error.message : 'Unknown error',
            body: req.body
        });
        res.status(400).json({
            error: error instanceof Error ? error.message : 'Failed to enrich bookmark'
        });
    }
});

export { router as bookmarkRouter }; 