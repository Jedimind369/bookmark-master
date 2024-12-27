import { useQuery } from "@tanstack/react-query";
import { BookmarkCard } from "../molecules/BookmarkCard";
import { fetchBookmarks } from "@/lib/api";
import { LoadingSpinner } from "../atoms/LoadingSpinner";
import { Bookmark } from "@/types/bookmark";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface BookmarkListProps {
  onEdit: (bookmark: Bookmark) => void;
  onDelete: (id: number) => void;
  onRefresh: (bookmark: Bookmark) => void;
}

export const BookmarkList = ({ onEdit, onDelete, onRefresh }: BookmarkListProps) => {
  const { data: bookmarks, isLoading, error } = useQuery({
    queryKey: ['/api/bookmarks'],
    queryFn: fetchBookmarks
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          Failed to load bookmarks. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  if (!bookmarks?.length) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        No bookmarks found. Add your first bookmark to get started!
      </div>
    );
  }

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
      {bookmarks.map((bookmark) => (
        <BookmarkCard
          key={bookmark.id}
          bookmark={bookmark}
          onEdit={onEdit}
          onDelete={() => onDelete(bookmark.id)}
          onRefresh={onRefresh}
        />
      ))}
    </div>
  );
};