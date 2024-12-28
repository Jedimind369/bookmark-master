import { FC } from "react";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Edit2, Trash2, ExternalLink, RefreshCw } from "lucide-react";
import { Bookmark } from "@/types/bookmark";

interface BookmarkCardProps {
  bookmark: Bookmark;
  onEdit: (bookmark: Bookmark) => void;
  onDelete: (bookmark: Bookmark) => void;
  onRefresh?: (bookmark: Bookmark) => void;
}

export const BookmarkCard: FC<BookmarkCardProps> = ({ 
  bookmark, 
  onEdit, 
  onDelete,
  onRefresh 
}) => {
  const combinedTags = Array.from(new Set([
    ...(bookmark.tags || []),
    ...(bookmark.analysis?.mainTopics || [])
  ]));

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <h3 className="text-lg font-semibold line-clamp-1">
            {bookmark.analysis?.title || bookmark.title}
          </h3>
          <div className="flex gap-2">
            {onRefresh && (
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => onRefresh(bookmark)}
                disabled={bookmark.analysis?.status === 'processing'}
                className="relative"
              >
                <RefreshCw className={`h-4 w-4 ${bookmark.analysis?.status === 'processing' ? 'animate-spin' : ''}`} />
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={() => onEdit(bookmark)}>
              <Edit2 className="h-4 w-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => onDelete(bookmark)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" asChild>
              <a href={bookmark.url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
          {bookmark.description || 'No description available'}
        </p>
        <div className="flex flex-wrap gap-2">
          {combinedTags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 bg-primary/10 text-primary rounded-md text-sm"
            >
              {tag}
            </span>
          ))}
        </div>
      </CardContent>
      <CardFooter className="pt-4">
        {bookmark.analysis?.contentQuality && (
          <div className="text-sm text-muted-foreground w-full">
            <div className="flex justify-between">
              <span>Quality Score:</span>
              <span className="font-medium">
                {Math.round(bookmark.analysis.contentQuality.overallScore * 100)}%
              </span>
            </div>
          </div>
        )}
      </CardFooter>
    </Card>
  );
};