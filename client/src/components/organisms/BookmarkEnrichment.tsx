import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Wand2, Loader2 } from "lucide-react";

interface EnrichmentStatus {
  processedCount: number;
  totalCount: number;
  status: "idle" | "processing" | "completed" | "error";
  message?: string;
}

export const BookmarkEnrichment = () => {
  const [enrichmentStatus, setEnrichmentStatus] = useState<EnrichmentStatus>({
    processedCount: 0,
    totalCount: 0,
    status: "idle"
  });
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Query to get the count of bookmarks that can be enriched
  const { data: enrichmentCount } = useQuery({
    queryKey: ["/api/bookmarks/enrich/count"],
    // Refresh every minute
    refetchInterval: 60000,
  });

  // Poll enrichment status when processing
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    if (enrichmentStatus.status === "processing" || enrichmentStatus.status === "completed") {
      pollInterval = setInterval(async () => {
        try {
          const response = await fetch("/api/bookmarks/enrich/status");
          if (!response.ok) throw new Error("Failed to get enrichment status");

          const status = await response.json();
          setEnrichmentStatus(status);

          if (status.status === "completed" || status.status === "error") {
            clearInterval(pollInterval);
            if (status.status === "completed") {
              queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
              queryClient.invalidateQueries({ queryKey: ["/api/bookmarks/enrich/count"] });
              toast({
                title: "Success",
                description: "All bookmarks have been enriched with AI analysis",
              });
            }
          }
        } catch (error) {
          console.error("Error polling enrichment status:", error);
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [enrichmentStatus.status, queryClient, toast]);

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
      setEnrichmentStatus({
        processedCount: 0,
        totalCount: data.count,
        status: "processing",
        message: `Starting enrichment of ${data.count} bookmarks...`
      });
    },
    onError: (error: Error) => {
      toast({
        variant: "destructive",
        title: "Error",
        description: error.message || "Failed to start enrichment process",
      });
      setEnrichmentStatus(prev => ({ ...prev, status: "error" }));
    },
  });

  const getProgressStatus = () => {
    if (enrichmentStatus.status === "processing" || enrichmentStatus.status === "completed") {
      const progress = Math.round((enrichmentStatus.processedCount / enrichmentStatus.totalCount) * 100);
      return (
        <Alert>
          <AlertDescription className="flex items-center gap-4">
            <Progress value={progress} className="w-[200px]" />
            <span className="text-sm text-muted-foreground">
              {enrichmentStatus.processedCount} of {enrichmentStatus.totalCount} enriched
              {enrichmentStatus.status === "completed" ? " (Completed)" : ""}
            </span>
            {enrichmentStatus.status === "processing" && enrichmentStatus.processedCount < enrichmentStatus.totalCount && 
              <Loader2 className="h-4 w-4 animate-spin" />
            }
          </AlertDescription>
        </Alert>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      <Button 
        variant="outline" 
        onClick={() => enrichMutation.mutate()}
        disabled={enrichMutation.isPending || enrichmentStatus.status === "processing" || enrichmentCount === 0}
      >
        <Wand2 className="h-4 w-4 mr-2" />
        Enrich Bookmarks {enrichmentCount ? `(${enrichmentCount})` : ''}
      </Button>
      {getProgressStatus()}
    </div>
  );
};