
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
    queryKey: ["enrichmentCount"],
    queryFn: async () => {
      const response = await fetch("/api/bookmarks/enrich/count");
      if (!response.ok) throw new Error("Failed to get enrichment count");
      return response.json();
    }
  });

  const pollStatus = async () => {
    try {
      const response = await fetch("/api/bookmarks/enrich/status");
      if (!response.ok) throw new Error("Failed to get enrichment status");
      const status = await response.json();
      
      const isComplete = status.processedCount === status.totalCount;
      setEnrichmentStatus({
        ...status,
        status: isComplete ? "completed" : "processing",
        message: isComplete 
          ? "All bookmarks have been analyzed!"
          : `Analyzing bookmark ${status.processedCount + 1} of ${status.totalCount}...`
      });

      if (isComplete) {
        queryClient.invalidateQueries({ queryKey: ["enrichmentCount"] });
        queryClient.invalidateQueries({ queryKey: ["bookmarks"] });
        toast({
          title: "Success",
          description: "All bookmarks have been enriched with AI analysis",
        });
        return true;
      }
      return false;
    } catch (error) {
      console.error("[Enrichment] Error polling status:", error);
      setEnrichmentStatus(prev => ({ ...prev, status: "error" }));
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to get enrichment status",
      });
      return true;
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (enrichmentStatus.status === "processing") {
      interval = setInterval(async () => {
        const shouldStop = await pollStatus();
        if (shouldStop) {
          clearInterval(interval);
        }
      }, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [enrichmentStatus.status]);

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
    onSuccess: () => {
      setEnrichmentStatus({
        processedCount: 0,
        totalCount: enrichmentCount || 0,
        status: "processing",
        message: "Starting analysis..."
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

  const isProcessing = enrichmentStatus.status === "processing";
  const progress = enrichmentStatus.totalCount > 0 
    ? Math.round((enrichmentStatus.processedCount / enrichmentStatus.totalCount) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <Button 
        variant={isProcessing ? "secondary" : "default"}
        onClick={() => enrichMutation.mutate()}
        disabled={isProcessing || !enrichmentCount}
        className="w-full sm:w-auto"
      >
        {isProcessing ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Wand2 className="h-4 w-4 mr-2" />
            Analyze Bookmarks {enrichmentCount ? `(${enrichmentCount})` : ''}
          </>
        )}
      </Button>

      {(isProcessing || enrichmentStatus.status === "completed") && (
        <div className="mt-4 p-6 bg-card border rounded-lg shadow-sm">
          <div className="space-y-4">
            <div className="flex items-center justify-between text-card-foreground">
              <div className="flex items-center gap-2">
                {isProcessing && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                <h3 className="text-lg font-semibold">
                  {enrichmentStatus.status === "completed" ? "Analysis Complete!" : "Analyzing Bookmarks..."}
                </h3>
              </div>
              <div className="text-lg font-bold text-primary">
                {progress}%
              </div>
            </div>

            <Progress value={progress} className="h-2" />

            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Processed {enrichmentStatus.processedCount} of {enrichmentStatus.totalCount} bookmarks
              </span>
              {enrichmentStatus.message && (
                <span>{enrichmentStatus.message}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {enrichmentStatus.status === "error" && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to process bookmarks. Please try again.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
