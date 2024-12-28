# AI-Powered Bookmark Management System

An advanced bookmark management system that transforms digital content organization through intelligent analysis and smart management tools.

## Features

- Intelligent bookmark analysis with AI-powered content insights
- Multi-language support
- Advanced content parsing and categorization
- Smart tagging and organization
- Rich content previews
- Bookmark health monitoring
- Bulk import/export capabilities

## Tech Stack

- Frontend: React with TypeScript
- Backend: Express.js with AI integration
- Database: PostgreSQL with Drizzle ORM
- AI: Anthropic Claude for content analysis
- UI: ShadcN components with Tailwind CSS

## Prerequisites

- Node.js 18+ 
- PostgreSQL database
- Anthropic API key

## Environment Variables

The following environment variables are required:

```env
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=your_api_key
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Jedimind369/bookmark-master.git
cd bookmark-master
```

2. Install dependencies:
```bash
npm install
```

3. Set up the database:
```bash
npm run db:push
```

4. Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:5000

## API Endpoints

### Bookmarks
- `GET /api/bookmarks` - List all bookmarks
- `POST /api/bookmarks` - Create bookmark
- `PUT /api/bookmarks/:id` - Update bookmark
- `DELETE /api/bookmarks/:id` - Delete bookmark

### Analysis
- `POST /api/bookmarks/analyze` - Analyze URL
- `GET /api/bookmarks/health` - Get health statistics
- `GET /api/bookmarks/enrich/count` - Get enrichment queue count
- `POST /api/bookmarks/enrich` - Start enrichment process

### Import/Export
- `POST /api/bookmarks/import` - Bulk import bookmarks
- `POST /api/bookmarks/parse-html` - Parse HTML bookmarks
- `DELETE /api/bookmarks/purge` - Purge all bookmarks

## Development

The project uses modern development practices and tools:

- TypeScript for type safety
- React Query for data fetching
- Drizzle ORM for database operations
- ShadcN UI components
- Tailwind CSS for styling

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
