
import { Bookmark } from "@/types/bookmark";

export const fetchBookmarks = async (): Promise<Bookmark[]> => {
  const response = await fetch('/api/bookmarks');
  if (!response.ok) {
    throw new Error('Failed to fetch bookmarks');
  }
  return response.json();
};
