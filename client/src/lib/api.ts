
import { Bookmark } from "@/types/bookmark";

export const fetchBookmarks = async (): Promise<Bookmark[]> => {
  const response = await fetch('/api/bookmarks');
  if (!response.ok) {
    throw new Error('Failed to fetch bookmarks');
  }
  return response.json();
};

export const updateBookmark = async (data: Partial<Bookmark>): Promise<Bookmark> => {
  const response = await fetch(`/api/bookmarks/${data.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    throw new Error('Failed to update bookmark');
  }
  return response.json();
};
