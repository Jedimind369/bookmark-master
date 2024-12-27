import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Upload } from "lucide-react";

export const BookmarkImport = () => {
  const [importing, setImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const importMutation = useMutation({
    mutationFn: async (bookmarks: any[]) => {
      console.log('[Import] Starting import mutation with', bookmarks.length, 'bookmarks');
      const response = await fetch("/api/bookmarks/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bookmarks),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to import bookmarks");
      }

      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
      toast({
        title: "Success",
        description: `${data.count} bookmarks imported successfully`,
      });
      setImporting(false);
      setProgress(0);
    },
    onError: (error: Error) => {
      console.error('[Import] Import error:', error);
      toast({
        variant: "destructive",
        title: "Import Error",
        description: error.message || "Failed to import bookmarks",
      });
      setImporting(false);
      setProgress(0);
    },
  });

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check file size before processing
    if (file.size > 50 * 1024 * 1024) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "File size too large. Maximum size is 50MB.",
      });
      return;
    }

    setImporting(true);
    setProgress(10);

    try {
      console.log('[Import] Reading file:', file.name);
      const text = await file.text();
      let bookmarks;

      setProgress(30);

      if (file.name.endsWith('.json')) {
        console.log('[Import] Parsing JSON file');
        try {
          bookmarks = JSON.parse(text);
        } catch (error) {
          throw new Error("Invalid JSON format. Please check your file.");
        }
      } else if (file.name.endsWith('.html')) {
        console.log('[Import] Processing HTML file');
        const response = await fetch('/api/bookmarks/parse-html', {
          method: 'POST',
          headers: { 'Content-Type': 'text/html' },
          body: text,
        });

        if (!response.ok) {
          if (response.status === 413) {
            throw new Error('File size too large. Maximum size is 50MB.');
          }
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to parse HTML bookmarks');
        }

        bookmarks = await response.json();
        console.log('[Import] Parsed bookmarks:', bookmarks);
      } else {
        throw new Error("Unsupported file format. Please upload a JSON or HTML file.");
      }

      if (!Array.isArray(bookmarks)) {
        throw new Error("Invalid file format. Expected an array of bookmarks.");
      }

      setProgress(50);
      console.log('[Import] Starting import of', bookmarks.length, 'bookmarks');
      await importMutation.mutateAsync(bookmarks);
    } catch (error) {
      console.error('[Import] Error during import:', error);
      toast({
        variant: "destructive",
        title: "Import Error",
        description: error instanceof Error ? error.message : "Failed to process the import file",
      });
      setImporting(false);
      setProgress(0);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <input
          type="file"
          accept=".json,.html"
          onChange={handleFileUpload}
          disabled={importing}
          className="hidden"
          id="import-file"
        />
        <label htmlFor="import-file">
          <Button asChild disabled={importing}>
            <span>
              <Upload className="h-4 w-4 mr-2" />
              {importing ? "Importing..." : "Import Bookmarks"}
            </span>
          </Button>
        </label>
        {importing && (
          <Progress value={progress} className="w-[200px]" />
        )}
      </div>
      {importing && (
        <Alert>
          <AlertDescription>
            Importing bookmarks... This may take a few minutes for large files.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};