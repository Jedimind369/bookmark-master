
ALTER TABLE bookmarks 
ADD COLUMN IF NOT EXISTS update_history JSONB DEFAULT '[]';
