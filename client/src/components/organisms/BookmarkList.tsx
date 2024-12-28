import { useQuery } from "@tanstack/react-query";
import { BookmarkCard } from "../molecules/BookmarkCard";
import { LoadingSpinner } from "../atoms/LoadingSpinner";
import { Bookmark } from "@/types/bookmark";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface BookmarkListProps {
  isLoading?: boolean;
  isAddingBookmark?: boolean;
  onAddBookmark?: () => void;
  onCancelAdd?: () => void;
}

export const BookmarkList = ({ 
  isLoading,
  isAddingBookmark,
  onAddBookmark,
  onCancelAdd 
}: BookmarkListProps) => {
  const { data: bookmarks = [], isLoading: isLoadingQuery, error } = useQuery<Bookmark[]>({
    queryKey: ['/api/bookmarks'],
  });

  if (isLoading || isLoadingQuery) {
    return (
      <div className="p-8 flex justify-center">
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

  if (!bookmarks?.length && !isAddingBookmark) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        <p className="mb-4">No bookmarks found. Add your first bookmark to get started!</p>
        {onAddBookmark && (
          <button
            onClick={onAddBookmark}
            className="text-primary hover:underline"
          >
            Add Bookmark
          </button>
        )}
      </div>
    );
  }

  // Sort bookmarks by date added
  const sortedBookmarks = [...bookmarks].sort((a, b) => {
    const dateA = new Date(a.dateAdded).getTime();
    const dateB = new Date(b.dateAdded).getTime();
    return dateB - dateA;
  });

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
      {sortedBookmarks.map((bookmark) => (
        <BookmarkCard
          key={bookmark.id}
          bookmark={bookmark}
          onEdit={() => {}} // Will implement these handlers later
          onDelete={() => {}}
        />
      ))}
    </div>
  );
};