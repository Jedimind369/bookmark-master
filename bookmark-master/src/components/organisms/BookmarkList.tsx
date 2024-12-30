
import { useBookmarkStore } from "@/store/bookmarkStore";
import { BookmarkCard } from "../molecules/BookmarkCard";
import { LoadingSpinner } from "../atoms/LoadingSpinner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

interface BookmarkListProps {
  onEdit: (bookmark: Bookmark) => void;
  onDelete: (id: string) => void;
}

export const BookmarkList = ({ onEdit, onDelete }: BookmarkListProps) => {
  const { filteredBookmarks, isLoading, error } = useBookmarkStore();

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

  if (!filteredBookmarks?.length) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        No bookmarks found. Add your first bookmark to get started!
      </div>
    );
  }

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
      {filteredBookmarks.map((bookmark) => (
        <BookmarkCard
          key={bookmark.id}
          bookmark={bookmark}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};
