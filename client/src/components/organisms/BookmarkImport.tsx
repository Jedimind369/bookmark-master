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
      const response = await fetch("/api/bookmarks/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bookmarks),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message);
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
      toast({
        variant: "destructive",
        title: "Error",
        description: error.message || "Failed to import bookmarks",
      });
      setImporting(false);
      setProgress(0);
    },
  });

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setProgress(0);

    try {
      const text = await file.text();
      let bookmarks;

      if (file.name.endsWith('.json')) {
        bookmarks = JSON.parse(text);
      } else if (file.name.endsWith('.html')) {
        const response = await fetch('/api/bookmarks/parse-html', {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain' },
          body: text,
        });

        if (!response.ok) {
          throw new Error('Failed to parse HTML bookmarks');
        }

        bookmarks = await response.json();
      } else {
        toast({
          variant: "destructive",
          title: "Error",
          description: "Unsupported file format. Please upload a JSON or HTML file.",
        });
        setImporting(false);
        return;
      }

      if (!Array.isArray(bookmarks)) {
        toast({
          variant: "destructive",
          title: "Error",
          description: "Invalid file format. Expected an array of bookmarks.",
        });
        setImporting(false);
        return;
      }

      setProgress(50);
      await importMutation.mutateAsync(bookmarks);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to parse the import file",
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
              Import Bookmarks
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