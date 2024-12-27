
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Bookmark } from "@/types/bookmark";

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // If this is a new bookmark, analyze with AI first
      if (!initialData?.id) {
        const enrichResponse = await fetch('/api/bookmarks/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: formData.url })
        });
        
        if (enrichResponse.ok) {
          const analysis = await enrichResponse.json();
          formData.title = formData.title || analysis.title;
          formData.description = formData.description || analysis.description;
          formData.tags = formData.tags || analysis.tags.join(", ");
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

      const result = await onSubmit(submitData);
      if (!result) {
        throw new Error('Failed to update bookmark');
      }
      console.log('Update result:', result);
      
      if (initialData?.id) {
        try {
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
      throw error;
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
