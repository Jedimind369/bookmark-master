import { FC } from "react";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Edit2, Trash2, ExternalLink } from "lucide-react";
import { Bookmark } from "@/types/bookmark";

interface BookmarkCardProps {
  bookmark: Bookmark;
  onEdit: (bookmark: Bookmark) => void;
  onDelete: (id: string) => void;
}

export const BookmarkCard: FC<BookmarkCardProps> = ({ bookmark, onEdit, onDelete }) => {
  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <h3 className="text-lg font-semibold line-clamp-1">{bookmark.title}</h3>
          <div className="flex gap-2">
            <Button variant="ghost" size="icon" onClick={() => onEdit(bookmark)}>
              <Edit2 className="h-4 w-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => onDelete(bookmark.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
          {bookmark.description || 'No description available'}
        </p>
        <div className="flex flex-wrap gap-2">
          {bookmark.tags?.map((tag) => (
            <div key={tag} className="px-2 py-1 bg-primary/10 text-primary rounded-md text-sm">
              {tag}
            </div>
          ))}
        </div>
      </CardContent>
      <CardFooter>
        <Button 
          variant="outline" 
          size="sm"
          onClick={() => window.open(bookmark.url, '_blank')}
          className="w-full"
        >
          <ExternalLink className="h-4 w-4 mr-2" />
          Visit Site
        </Button>
      </CardFooter>
    </Card>
  );
};