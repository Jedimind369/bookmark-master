
# API Endpoints

## Bookmarks
- GET /api/bookmarks - List all bookmarks
- POST /api/bookmarks - Create bookmark
- PUT /api/bookmarks/:id - Update bookmark
- DELETE /api/bookmarks/:id - Delete bookmark

## Analysis
- POST /api/bookmarks/analyze - Analyze URL
- GET /api/bookmarks/health - Get health statistics
- GET /api/bookmarks/enrich/count - Get enrichment queue count
- POST /api/bookmarks/enrich - Start enrichment process

## Import/Export
- POST /api/bookmarks/import - Bulk import bookmarks
- POST /api/bookmarks/parse-html - Parse HTML bookmarks
- DELETE /api/bookmarks/purge - Purge all bookmarks
