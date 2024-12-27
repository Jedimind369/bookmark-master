import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Bookmark, CreateBookmarkDto, UpdateBookmarkDto } from '@/types/bookmark';

interface BookmarkState {
  // State
  bookmarks: Bookmark[];
  filteredBookmarks: Bookmark[];
  searchQuery: string;
  selectedTags: string[];
  selectedCollections: string[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setBookmarks: (bookmarks: Bookmark[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSearchQuery: (query: string) => void;
  setSelectedTags: (tags: string[]) => void;
  setSelectedCollections: (collections: string[]) => void;
  
  // Filter actions
  filterBookmarks: () => void;
  clearFilters: () => void;
  
  // CRUD actions
  addBookmark: (bookmark: Bookmark) => void;
  updateBookmark: (id: string, bookmark: Partial<Bookmark>) => void;
  deleteBookmark: (id: string) => void;
  
  // Utility actions
  getUniqueTags: () => string[];
  getUniqueCollections: () => string[];
}

export const useBookmarkStore = create<BookmarkState>()(
  devtools(
    (set, get) => ({
      // Initial state
      bookmarks: [],
      filteredBookmarks: [],
      searchQuery: '',
      selectedTags: [],
      selectedCollections: [],
      isLoading: false,
      error: null,

      // State setters
      setBookmarks: (bookmarks) =>
        set((state) => {
          return {
            bookmarks,
            filteredBookmarks: bookmarks,
          };
        }),

      setLoading: (loading) => set({ isLoading: loading }),
      
      setError: (error) => set({ error }),

      setSearchQuery: (query) =>
        set(
          (state) => {
            return {
              searchQuery: query,
            };
          },
          false,
          'setSearchQuery'
        ),

      setSelectedTags: (tags) =>
        set(
          (state) => {
            return {
              selectedTags: tags,
            };
          },
          false,
          'setSelectedTags'
        ),

      setSelectedCollections: (collections) =>
        set(
          (state) => {
            return {
              selectedCollections: collections,
            };
          },
          false,
          'setSelectedCollections'
        ),

      // Filter implementation
      filterBookmarks: () =>
        set((state) => {
          let filtered = [...state.bookmarks];

          // Apply search filter
          if (state.searchQuery) {
            const query = state.searchQuery.toLowerCase();
            filtered = filtered.filter(
              (bookmark) =>
                bookmark.title.toLowerCase().includes(query) ||
                bookmark.description?.toLowerCase().includes(query) ||
                bookmark.url.toLowerCase().includes(query)
            );
          }

          // Apply tag filter
          if (state.selectedTags.length > 0) {
            filtered = filtered.filter((bookmark) =>
              state.selectedTags.some((tag) => bookmark.tags.includes(tag))
            );
          }

          // Apply collection filter
          if (state.selectedCollections.length > 0) {
            filtered = filtered.filter((bookmark) =>
              state.selectedCollections.some((collection) =>
                bookmark.collections.includes(collection)
              )
            );
          }

          return {
            filteredBookmarks: filtered,
          };
        }),

      clearFilters: () =>
        set((state) => ({
          searchQuery: '',
          selectedTags: [],
          selectedCollections: [],
          filteredBookmarks: state.bookmarks,
        })),

      // CRUD operations
      addBookmark: (bookmark) =>
        set((state) => {
          const newBookmarks = [...state.bookmarks, bookmark];
          return {
            bookmarks: newBookmarks,
            filteredBookmarks: newBookmarks,
          };
        }),

      updateBookmark: (id, updatedBookmark) =>
        set((state) => {
          const newBookmarks = state.bookmarks.map((bookmark) =>
            bookmark.id === id
              ? { ...bookmark, ...updatedBookmark }
              : bookmark
          );
          return {
            bookmarks: newBookmarks,
            filteredBookmarks: newBookmarks,
          };
        }),

      deleteBookmark: (id) =>
        set((state) => {
          const newBookmarks = state.bookmarks.filter(
            (bookmark) => bookmark.id !== id
          );
          return {
            bookmarks: newBookmarks,
            filteredBookmarks: newBookmarks,
          };
        }),

      // Utility functions
      getUniqueTags: () => {
        const state = get();
        const tags = new Set<string>();
        state.bookmarks.forEach((bookmark) => {
          bookmark.tags.forEach((tag) => tags.add(tag));
        });
        return Array.from(tags);
      },

      getUniqueCollections: () => {
        const state = get();
        const collections = new Set<string>();
        state.bookmarks.forEach((bookmark) => {
          bookmark.collections.forEach((collection) =>
            collections.add(collection)
          );
        });
        return Array.from(collections);
      },
    }),
    {
      name: 'bookmark-store',
    }
  )
);
