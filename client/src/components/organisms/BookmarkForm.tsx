import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Bookmark } from "@/types/bookmark";
import { useToast } from "@/hooks/use-toast";

interface BookmarkFormProps {
  initialData?: Bookmark;
  onSubmit: (data: Partial<Bookmark>) => Promise<Bookmark>;
  onCancel: () => void;
}

export const BookmarkForm = ({ initialData, onSubmit, onCancel }: BookmarkFormProps) => {
  const [formData, setFormData] = useState({
    title: initialData?.title || "",
    url: initialData?.url || "",
    description: initialData?.description || "",
    tags: (initialData?.tags || []).join(", "),
  });
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      console.log('Starting bookmark submission with URL:', formData.url);

      // If this is a new bookmark, analyze with AI first
      if (!initialData?.id) {
        try {
          console.log('Analyzing URL with AI...');
          const enrichResponse = await fetch('/api/bookmarks/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: formData.url })
          });

          if (!enrichResponse.ok) {
            const error = await enrichResponse.json();
            throw new Error(error.message || 'Failed to analyze URL');
          }

          const analysis = await enrichResponse.json();
          console.log('AI analysis result:', analysis);

          formData.title = formData.title || analysis.title;
          formData.description = formData.description || analysis.description;
          if (analysis.tags && analysis.tags.length > 0) {
            formData.tags = formData.tags || analysis.tags.join(", ");
          }
        } catch (error) {
          console.error('Error during AI analysis:', error);
          toast({
            variant: "destructive",
            title: "Analysis Error",
            description: error instanceof Error ? error.message : "Failed to analyze URL"
          });
        }
      }

      const tags = formData.tags.split(",").map((tag) => tag.trim()).filter(Boolean);

      const submitData = {
        id: initialData?.id,
        title: formData.title || initialData?.title,
        url: formData.url || initialData?.url,
        description: formData.description,
        tags: tags,
        collections: initialData?.collections || [],
        dateModified: new Date(),
        analysis: initialData?.analysis
      };

      if (!submitData.title || !submitData.url) {
        throw new Error('Title and URL are required');
      }

      console.log('Submitting bookmark data:', submitData);
      const result = await onSubmit(submitData);
      if (!result) {
        throw new Error('Failed to update bookmark');
      }
      console.log('Bookmark submission successful:', result);

      // If this is an existing bookmark, trigger enrichment
      if (initialData?.id) {
        try {
          console.log('Triggering enrichment for existing bookmark');
          await fetch('/api/bookmarks/enrich', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: [initialData.id] })
          });
        } catch (error) {
          console.error('Failed to trigger enrichment:', error);
        }
      }

      onCancel();
    } catch (error) {
      console.error('Error updating bookmark:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save bookmark"
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Input
          placeholder="Title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          required
        />
      </div>
      <div>
        <Input
          placeholder="URL"
          type="url"
          value={formData.url}
          onChange={(e) => setFormData({ ...formData, url: e.target.value })}
          required
        />
      </div>
      <div>
        <Textarea
          placeholder="Description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        />
      </div>
      <div>
        <Input
          placeholder="Tags (comma-separated)"
          value={formData.tags}
          onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {initialData ? "Update" : "Add"} Bookmark
        </Button>
      </div>
    </form>
  );
};