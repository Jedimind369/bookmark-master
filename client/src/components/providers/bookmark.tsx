import { createContext, useContext, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Bookmark } from "@/types/bookmark";

interface BookmarkContextType {
  bookmarks: Bookmark[];
  isLoading: boolean;
  error: Error | null;
  addBookmark: (bookmark: Partial<Bookmark>) => Promise<void>;
  updateBookmark: (id: string, bookmark: Partial<Bookmark>) => Promise<void>;
  deleteBookmark: (id: string) => Promise<void>;
}

const BookmarkContext = createContext<BookmarkContextType | null>(null);

export function BookmarkProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  // Fetch bookmarks
  const { data: bookmarks = [], isLoading, error } = useQuery<Bookmark[]>({
    queryKey: ['/api/bookmarks'],
  });

  // Add bookmark
  const addBookmarkMutation = useMutation({
    mutationFn: async (bookmark: Partial<Bookmark>) => {
      const response = await fetch('/api/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookmark),
      });
      if (!response.ok) throw new Error('Failed to add bookmark');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/bookmarks'] });
    },
  });

  // Update bookmark
  const updateBookmarkMutation = useMutation({
    mutationFn: async ({ id, bookmark }: { id: string; bookmark: Partial<Bookmark> }) => {
      const response = await fetch(`/api/bookmarks/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookmark),
      });
      if (!response.ok) throw new Error('Failed to update bookmark');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/bookmarks'] });
    },
  });

  // Delete bookmark
  const deleteBookmarkMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`/api/bookmarks/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete bookmark');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/bookmarks'] });
    },
  });

  const addBookmark = useCallback(async (bookmark: Partial<Bookmark>) => {
    await addBookmarkMutation.mutateAsync(bookmark);
  }, [addBookmarkMutation]);

  const updateBookmark = useCallback(async (id: string, bookmark: Partial<Bookmark>) => {
    await updateBookmarkMutation.mutateAsync({ id, bookmark });
  }, [updateBookmarkMutation]);

  const deleteBookmark = useCallback(async (id: string) => {
    await deleteBookmarkMutation.mutateAsync(id);
  }, [deleteBookmarkMutation]);

  return (
    <BookmarkContext.Provider
      value={{
        bookmarks,
        isLoading,
        error: error as Error | null,
        addBookmark,
        updateBookmark,
        deleteBookmark,
      }}
    >
      {children}
    </BookmarkContext.Provider>
  );
}

export const useBookmarks = () => {
  const context = useContext(BookmarkContext);
  if (!context) {
    throw new Error('useBookmarks must be used within a BookmarkProvider');
  }
  return context;
};
