import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Wand2 } from "lucide-react";

export const BookmarkEnrichment = () => {
  const [enriching, setEnriching] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Query to get the count of bookmarks that can be enriched
  const { data: enrichmentCount } = useQuery({
    queryKey: ["/api/bookmarks/enrich/count"],
    // Refresh every minute
    refetchInterval: 60000,
  });

  const enrichMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/bookmarks/enrich", {
        method: "POST",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message);
      }

      return response.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Started Enrichment",
        description: `${data.count} bookmarks will be enriched with comprehensive analysis`,
      });
      setEnriching(true);

      // Refresh bookmarks after a delay to show updated analysis
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
        queryClient.invalidateQueries({ queryKey: ["/api/bookmarks/enrich/count"] });
        setEnriching(false);
      }, 5000);
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Error",
        description: error.message || "Failed to start enrichment process",
      });
      setEnriching(false);
    },
  });

  if (enriching) {
    return (
      <Alert>
        <AlertDescription className="flex items-center gap-2">
          <Progress value={100} className="w-[100px]" />
          Enriching bookmarks with comprehensive analysis...
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Button 
      variant="outline" 
      onClick={() => enrichMutation.mutate()}
      disabled={enrichMutation.isPending || enrichmentCount === 0}
    >
      <Wand2 className="h-4 w-4 mr-2" />
      Enrich Bookmarks {enrichmentCount ? `(${enrichmentCount})` : ''}
    </Button>
  );
};