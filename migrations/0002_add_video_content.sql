-- Add video content support to bookmarks table
ALTER TABLE bookmarks 
ADD COLUMN IF NOT EXISTS analysis jsonb DEFAULT NULL,
ADD COLUMN IF NOT EXISTS update_history jsonb DEFAULT '[]'::jsonb;
