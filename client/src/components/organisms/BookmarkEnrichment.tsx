
import { useState, useEffect } from "react";
import { Wand2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

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

  const { data: enrichmentCount } = useQuery({
    queryKey: ["/api/bookmarks/enrich/count"],
    refetchInterval: 60000,
  });

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    if (enrichmentStatus.status === "processing") {
      pollInterval = setInterval(async () => {
        try {
          const response = await fetch("/api/bookmarks/enrich/status");
          if (!response.ok) throw new Error("Failed to get enrichment status");

          const status = await response.json();
          setEnrichmentStatus(prev => {
            // Stop polling if we've processed all items or haven't made progress in a while
            if (status.processedCount === status.totalCount || 
                (prev.processedCount === status.processedCount && prev.processedCount > 0)) {
              clearInterval(pollInterval);
              // Force refetch bookmarks to get updated data
              queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
              return { ...status, status: "completed" };
            }
            return status;
          });

          if (status.status === "completed") {
            clearInterval(pollInterval);
            // Force refetch bookmarks to get updated data
            queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
            queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
            queryClient.invalidateQueries({ queryKey: ["/api/bookmarks/enrich/count"] });
            toast({
              title: "Success",
              description: "All bookmarks have been enriched with AI analysis",
            });
          }
        } catch (error) {
          console.error("Error polling enrichment status:", error);
          clearInterval(pollInterval);
          setEnrichmentStatus(prev => ({ ...prev, status: "error" }));
        }
      }, 5000);
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
    if (enrichmentStatus.status === "error") {
      return (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to process bookmarks. Please try again.
          </AlertDescription>
        </Alert>
      );
    }

    if (enrichmentStatus.status === "processing" || enrichmentStatus.status === "completed") {
      const progress = Math.round((enrichmentStatus.processedCount / enrichmentStatus.totalCount) * 100);
      const isComplete = enrichmentStatus.status === "completed" || 
                        enrichmentStatus.processedCount === enrichmentStatus.totalCount ||
                        progress >= 100;
      
      return (
        <Alert>
          <AlertDescription className="flex items-center gap-4">
            <Progress value={progress} className="w-[200px]" />
            <span className="text-sm text-muted-foreground">
              {enrichmentStatus.processedCount} of {enrichmentStatus.totalCount} processed
              {isComplete ? " (Completed)" : ""}
            </span>
            {!isComplete && <Loader2 className="h-4 w-4 animate-spin" />}
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
