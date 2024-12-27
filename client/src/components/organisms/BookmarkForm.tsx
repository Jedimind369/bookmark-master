
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Bookmark } from "@/types/bookmark";

interface BookmarkFormProps {
  initialData?: Bookmark;
  onSubmit: (data: Partial<Bookmark>) => void;
  onCancel: () => void;
}

export const BookmarkForm = ({ initialData, onSubmit, onCancel }: BookmarkFormProps) => {
  const [formData, setFormData] = useState({
    title: initialData?.analysis?.title || initialData?.title || "",
    url: initialData?.url || "",
    description: initialData?.analysis?.summary || initialData?.description || "",
    tags: (initialData?.analysis?.tags || initialData?.tags || []).join(", "),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const tags = formData.tags.split(",").map((tag) => tag.trim()).filter(Boolean);
      
      const submitData = {
        id: initialData?.id,
        title: formData.title,
        url: formData.url,
        description: formData.description,
        tags,
        analysis: initialData?.analysis
      };

      await onSubmit(submitData);
      
      if (initialData?.id) {
        const enrichResponse = await fetch('/api/bookmarks/enrich', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: [initialData.id] })
        });

        if (!enrichResponse.ok) {
          console.error('Failed to trigger enrichment');
        }
      }

      onCancel();
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: [initialData.id] })
        });
      }

      onCancel(); // Close the form after successful update
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
