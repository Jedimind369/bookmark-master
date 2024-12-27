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

  // Query to get initial count of bookmarks needing enrichment
  const { data: enrichmentCount = 0, error: countError } = useQuery({
    queryKey: ["/api/bookmarks/enrich/count"],
    refetchInterval: enrichmentStatus.status === "processing" ? 2000 : false,
    retry: false,
    onError: (error: Error) => {
      console.error("[Enrichment] Error fetching count:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to get enrichment count"
      });
    }
  });

  // Set up polling when enrichment is in progress
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        console.log("[Enrichment] Polling status...");
        const response = await fetch("/api/bookmarks/enrich/status");

        if (!response.ok) {
          throw new Error(`Status check failed: ${response.status}`);
        }

        const status = await response.json();
        console.log("[Enrichment] Status update:", status);

        setEnrichmentStatus(prev => {
          if (status.processedCount === status.totalCount) {
            console.log("[Enrichment] Process completed");
            clearInterval(pollInterval);
            queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
            toast({
              title: "Success",
              description: "All bookmarks have been enriched with AI analysis"
            });
            return {
              ...status,
              status: "completed",
              message: "Analysis complete!"
            };
          }

          return {
            ...status,
            status: "processing",
            message: `Analyzing bookmark ${status.processedCount + 1} of ${status.totalCount}...`
          };
        });
      } catch (error) {
        console.error("[Enrichment] Error polling status:", error);
        clearInterval(pollInterval);
        setEnrichmentStatus(prev => ({
          ...prev,
          status: "error",
          message: "Failed to get status update"
        }));
      }
    };

    if (enrichmentStatus.status === "processing") {
      console.log("[Enrichment] Starting status polling");
      pollStatus(); // Poll immediately
      pollInterval = setInterval(pollStatus, 2000);
    }

    return () => {
      if (pollInterval) {
        console.log("[Enrichment] Cleaning up polling interval");
        clearInterval(pollInterval);
      }
    };
  }, [enrichmentStatus.status, queryClient, toast]);

  const enrichMutation = useMutation({
    mutationFn: async () => {
      console.log("[Enrichment] Starting enrichment process");
      const response = await fetch("/api/bookmarks/enrich", {
        method: "POST"
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to start enrichment");
      }

      return response.json();
    },
    onMutate: () => {
      setEnrichmentStatus({
        processedCount: 0,
        totalCount: enrichmentCount,
        status: "processing",
        message: "Starting analysis..."
      });
    },
    onSuccess: (data) => {
      console.log("[Enrichment] Process started successfully:", data);
      if (data.count === 0) {
        setEnrichmentStatus(prev => ({ ...prev, status: "idle" }));
        toast({
          title: "No Action Needed",
          description: "All bookmarks are already analyzed."
        });
        return;
      }

      toast({
        title: "Starting Analysis",
        description: `Beginning analysis of ${data.count} bookmarks...`
      });
    },
    onError: (error: Error) => {
      console.error("[Enrichment] Error starting process:", error);
      setEnrichmentStatus(prev => ({
        ...prev,
        status: "error",
        message: error.message
      }));
      toast({
        variant: "destructive",
        title: "Error",
        description: error.message || "Failed to start enrichment process"
      });
    }
  });

  const isProcessing = enrichmentStatus.status === "processing";
  const getProgress = (processedCount: number, totalCount: number) => {
    if (totalCount === 0) return 0;
    // Ensure progress never exceeds 100%
    return Math.min(100, Math.round((processedCount / totalCount) * 100));
  };
  const progress = getProgress(enrichmentStatus.processedCount, enrichmentStatus.totalCount);

  if (countError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Failed to load enrichment status. Please refresh the page.
        </AlertDescription>
      </Alert>
    );
  }

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
            Analyze Bookmarks {enrichmentCount ? `(${enrichmentCount})` : ""}
          </>
        )}
      </Button>

      {(isProcessing || enrichmentStatus.status === "completed") && (
        <div className="mt-4 p-6 bg-card border rounded-lg shadow-sm">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isProcessing && (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                )}
                <h3 className="text-lg font-semibold text-primary">
                  {enrichmentStatus.status === "completed"
                    ? "Analysis Complete!"
                    : "Analyzing Bookmarks..."}
                </h3>
              </div>
              <div className="text-lg font-bold text-primary">
                {progress}%
              </div>
            </div>

            <Progress value={progress} className="h-4 transition-all" />

            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Processed {Math.min(enrichmentStatus.processedCount, enrichmentStatus.totalCount)} of{" "}
                {enrichmentStatus.totalCount} bookmarks
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
            {enrichmentStatus.message || "Failed to process bookmarks. Please try again."}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};