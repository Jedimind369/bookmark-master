import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Bookmark } from "@/types/bookmark";
import { useToast } from "@/hooks/use-toast";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface BookmarkFormProps {
  initialData?: Bookmark;
  onSubmit: (data: Partial<Bookmark>) => Promise<void>;
  onCancel: () => void;
}

export const BookmarkForm = ({ initialData, onSubmit, onCancel }: BookmarkFormProps) => {
  const [formData, setFormData] = useState({
    title: initialData?.title || "",
    url: initialData?.url || "",
    description: initialData?.description || "",
    tags: (initialData?.tags || []).join(", "),
  });
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const handleUrlChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setFormData(prev => ({ ...prev, url }));

    // If this is a new bookmark and we have a valid URL, trigger analysis
    if (!initialData?.id && url && url.startsWith('http')) {
      try {
        console.log('Starting URL analysis:', url);
        setAnalyzing(true);
        setError(null);

        const response = await fetch('/api/bookmarks/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });

        console.log('Analysis response status:', response.status);

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to analyze URL');
        }

        const analysis = await response.json();
        console.log('Analysis result:', analysis);

        // Update form with analysis results
        setFormData(prev => ({
          ...prev,
          title: prev.title || analysis.title || '',
          description: prev.description || analysis.description || '',
          tags: prev.tags || (analysis.tags ? analysis.tags.join(", ") : '')
        }));

        toast({
          title: "Analysis Complete",
          description: "URL has been analyzed successfully"
        });

      } catch (error) {
        console.error('Analysis error:', error);
        const message = error instanceof Error ? error.message : 'Failed to analyze URL';
        setError(message);
        toast({
          variant: "destructive",
          title: "Analysis Error",
          description: message
        });
      } finally {
        setAnalyzing(false);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      console.log('Starting bookmark submission');
      setError(null);

      const tags = formData.tags.split(",").map((tag) => tag.trim()).filter(Boolean);

      const submitData = {
        ...initialData, 
        title: formData.title,
        url: formData.url,
        description: formData.description,
        tags,
        dateModified: new Date().toISOString() 
      };

      console.log('Submitting bookmark data:', submitData);

      if (!submitData.title || !submitData.url) {
        throw new Error('Title and URL are required');
      }

      await onSubmit(submitData);

    } catch (error) {
      console.error('Submission error:', error);
      const message = error instanceof Error ? error.message : 'Failed to save bookmark';
      setError(message);
      toast({
        variant: "destructive",
        title: "Error",
        description: message
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div>
        <Input
          placeholder="URL"
          type="url"
          value={formData.url}
          onChange={handleUrlChange}
          disabled={analyzing}
          required
          className="mb-2"
        />
      </div>
      <div>
        <Input
          placeholder="Title"
          value={formData.title}
          onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
          disabled={analyzing}
          required
        />
      </div>
      <div>
        <Textarea
          placeholder="Description"
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          disabled={analyzing}
        />
      </div>
      <div>
        <Input
          placeholder="Tags (comma-separated)"
          value={formData.tags}
          onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
          disabled={analyzing}
        />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={analyzing}>
          Cancel
        </Button>
        <Button type="submit" disabled={analyzing}>
          {analyzing ? "Analyzing..." : initialData ? "Update" : "Add"} Bookmark
        </Button>
      </div>
    </form>
  );
};