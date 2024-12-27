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
  const { data: enrichmentCount, isError: isCountError } = useQuery({
    queryKey: ["/api/bookmarks/enrich/count"],
    onError: (error) => {
      console.error("[Enrichment] Error fetching count:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to get enrichment count",
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
          const isComplete = status.processedCount === status.totalCount;

          if (isComplete) {
            console.log("[Enrichment] Process completed");
            clearInterval(pollInterval);
            queryClient.invalidateQueries({ queryKey: ["/api/bookmarks"] });
            toast({
              title: "Success",
              description: "All bookmarks have been enriched with AI analysis",
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
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to get enrichment status",
        });
      }
    };

    if (enrichmentStatus.status === "processing") {
      console.log("[Enrichment] Starting status polling");
      // Poll immediately when starting
      pollStatus();
      // Then set up regular polling
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
        method: "POST",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to start enrichment");
      }

      return response.json();
    },
    onSuccess: (data) => {
      console.log("[Enrichment] Process started successfully:", data);
      if (data.count === 0) {
        toast({
          title: "No Action Needed",
          description: "All bookmarks are already analyzed.",
        });
        return;
      }

      setEnrichmentStatus({
        processedCount: 0,
        totalCount: data.count,
        status: "processing",
        message: `Starting analysis of ${data.count} bookmarks...`
      });

      toast({
        title: "Starting Analysis",
        description: `Beginning analysis of ${data.count} bookmarks...`,
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
        description: error.message || "Failed to start enrichment process",
      });
    },
  });

  const getProgressStatus = () => {
    // Always show the progress section when processing
    if (enrichmentStatus.status === "processing" || enrichmentStatus.status === "completed") {
      const progress = Math.round((enrichmentStatus.processedCount / enrichmentStatus.totalCount) * 100) || 0;
      const isComplete = enrichmentStatus.status === "completed";

      return (
        <div className="mt-4 p-6 bg-card border rounded-lg shadow-sm">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {!isComplete && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                <h3 className="text-lg font-semibold text-primary">
                  {isComplete ? "Analysis Complete!" : "Analyzing Bookmarks..."}
                </h3>
              </div>
              <div className="text-lg font-bold text-primary">
                {progress}%
              </div>
            </div>

            <Progress 
              value={progress} 
              className="h-4 transition-all"
            />

            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Processed {enrichmentStatus.processedCount} of {enrichmentStatus.totalCount} bookmarks
              </span>
              {enrichmentStatus.message && (
                <span className="text-muted-foreground">
                  {enrichmentStatus.message}
                </span>
              )}
            </div>
          </div>
        </div>
      );
    }

    if (enrichmentStatus.status === "error") {
      return (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>
            {enrichmentStatus.message || "Failed to process bookmarks. Please try again."}
          </AlertDescription>
        </Alert>
      );
    }

    return null;
  };

  const isProcessing = enrichmentStatus.status === "processing" || enrichMutation.isPending;

  // Don't render if we had an error getting the count
  if (isCountError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Failed to load enrichment status. Please refresh the page.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-2">
      <Button 
        variant={isProcessing ? "secondary" : "default"}
        onClick={() => enrichMutation.mutate()}
        disabled={isProcessing || !enrichmentCount}
        className="w-full sm:w-auto relative"
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
      {getProgressStatus()}
    </div>
  );
};