import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookmarkList } from "../organisms/BookmarkList";
import { BookmarkForm } from "../organisms/BookmarkForm";
import { BookmarkImport } from "../organisms/BookmarkImport";
import { BookmarkEnrichment } from "../organisms/BookmarkEnrichment";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Trash2 } from "lucide-react";
import { Bookmark, CreateBookmarkDto, UpdateBookmarkDto } from "@/types/bookmark";
import { useToast } from "@/hooks/use-toast";

export const Home = () => {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isPurgeDialogOpen, setIsPurgeDialogOpen] = useState(false);
  const [selectedBookmark, setSelectedBookmark] = useState<Bookmark | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const refreshMutation = useMutation({
    mutationFn: async (bookmark: Bookmark) => {
      console.log(`[Refresh] Refreshing analysis for bookmark ${bookmark.id}`);
      const response = await fetch(`/api/bookmarks/${bookmark.id}/analyze`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to refresh bookmark analysis");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
      toast({
        title: "Success",
        description: "Bookmark analysis refreshed",
      });
    },
    onError: () => {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to refresh bookmark analysis",
      });
    },
  });

  const purgeMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/bookmarks/purge", {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to purge bookmarks");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
      toast({
        title: "Success",
        description: "All bookmarks have been purged",
      });
      setIsPurgeDialogOpen(false);
    },
    onError: () => {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to purge bookmarks",
      });
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: CreateBookmarkDto) => {
      console.log('[Create] Creating new bookmark:', data);
      const response = await fetch("/api/bookmarks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Failed to create bookmark");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
      toast({
        title: "Success",
        description: "Bookmark created successfully",
      });
      handleCloseForm();
    },
    onError: () => {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to create bookmark",
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: UpdateBookmarkDto) => {
      console.log(`[Update] Updating bookmark ${data.id}:`, data);

      // First update the bookmark data
      const response = await fetch(`/api/bookmarks/${data.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Failed to update bookmark");
      const updatedBookmark = await response.json();

      // Then trigger a reanalysis
      console.log(`[Update] Refreshing analysis for bookmark ${data.id}`);
      const reanalyzeResponse = await fetch(`/api/bookmarks/${data.id}/analyze`, {
        method: "POST",
      });

      if (!reanalyzeResponse.ok) {
        throw new Error("Failed to refresh bookmark analysis after update");
      }

      return await reanalyzeResponse.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
      toast({
        title: "Success",
        description: "Bookmark updated and analysis refreshed",
      });
      handleCloseForm();
    },
    onError: () => {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to update bookmark",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      console.log(`[Delete] Deleting bookmark ${id}`);
      const response = await fetch(`/api/bookmarks/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete bookmark");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
      toast({
        title: "Success",
        description: "Bookmark deleted successfully",
      });
    },
    onError: () => {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to delete bookmark",
      });
    },
  });

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setSelectedBookmark(null);
  };

  const handleEdit = (bookmark: Bookmark) => {
    setSelectedBookmark(bookmark);
    setIsFormOpen(true);
  };

  const handleSubmit = async (data: Partial<Bookmark>) => {
    try {
      console.log('[Submit] Handling form submission:', data);
      if (data.id) {
        await updateMutation.mutateAsync({
          id: data.id,
          ...data,
        } as UpdateBookmarkDto);
      } else {
        await createMutation.mutateAsync(data as CreateBookmarkDto);
      }
    } catch (error) {
      console.error('[Submit] Error submitting bookmark:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save bookmark",
      });
    }
  };

  const handlePurge = () => {
    purgeMutation.mutate();
  };

  const handleRefresh = (bookmark: Bookmark) => {
    console.log(`[Refresh] Triggering refresh for bookmark ${bookmark.id}`);
    refreshMutation.mutate(bookmark);
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Bookmarks</h1>
        <div className="flex gap-4">
          <BookmarkEnrichment />
          <BookmarkImport />
          <Button
            variant="outline"
            onClick={() => setIsPurgeDialogOpen(true)}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Purge All
          </Button>
          <Button onClick={() => setIsFormOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Bookmark
          </Button>
        </div>
      </div>

      <BookmarkList
        onEdit={handleEdit}
        onDelete={(id) => deleteMutation.mutate(id)}
        onRefresh={handleRefresh}
      />

      <Dialog open={isPurgeDialogOpen} onOpenChange={setIsPurgeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Purge</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete all bookmarks? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsPurgeDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handlePurge}
              disabled={purgeMutation.isPending}
            >
              {purgeMutation.isPending ? "Purging..." : "Purge All"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {selectedBookmark ? "Edit Bookmark" : "Add New Bookmark"}
            </DialogTitle>
          </DialogHeader>
          <BookmarkForm
            initialData={selectedBookmark || undefined}
            onSubmit={handleSubmit}
            onCancel={handleCloseForm}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Home;