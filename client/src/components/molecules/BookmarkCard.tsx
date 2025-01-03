import { ArrowUpRight, Edit2, Trash2, RefreshCw } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader } from "../ui/card";
import { Tag } from "../atoms/Tag";
import { Bookmark } from "@/types/bookmark";

interface BookmarkCardProps {
  bookmark: Bookmark;
  onEdit: (bookmark: Bookmark) => void;
  onDelete: (bookmark: Bookmark) => void;
  onRefresh: (bookmark: Bookmark) => void;
}

export const BookmarkCard = ({ bookmark, onEdit, onDelete, onRefresh }: BookmarkCardProps) => {
  const combinedTags = Array.from(new Set([
    ...(bookmark.tags || []),
    ...(bookmark.analysis?.tags || [])
  ]));

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <h3 className="text-lg font-semibold line-clamp-1">
            {bookmark.analysis?.title || bookmark.title}
          </h3>
          <div className="flex gap-2">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => onRefresh(bookmark)}
              disabled={bookmark.analysis?.status === 'processing'}
              className="relative"
            >
              <RefreshCw className={`h-4 w-4 ${bookmark.analysis?.status === 'processing' ? 'animate-spin' : ''}`} />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => onEdit(bookmark)}>
              <Edit2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => onDelete(bookmark)}>
              <Trash2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" asChild>
              <a href={bookmark.url} target="_blank" rel="noopener noreferrer">
                <ArrowUpRight className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground">
          {bookmark.description && !bookmark.description.includes('Failed to fetch') 
            ? bookmark.description 
            : 'Unable to fetch details at this time'}
        </div>
        <div className="flex flex-wrap gap-2">
          {combinedTags.map((tag) => (
            <Tag key={tag} text={tag} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};