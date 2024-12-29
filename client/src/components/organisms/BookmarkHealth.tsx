import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { TokenUsageMeter } from "@/components/ui/token-meter";

export const BookmarkHealth = () => {
  const { data: health, error: healthError } = useQuery({
    queryKey: ["/api/bookmarks/health"],
    queryFn: async () => {
      const response = await fetch("/api/bookmarks/health");
      if (!response.ok) throw new Error("Failed to fetch health status");
      return response.json();
    }
  });

  const { data: tokenUsage, error: tokenError } = useQuery({
    queryKey: ["/api/bookmarks/token-usage"],
    queryFn: async () => {
      const response = await fetch("/api/bookmarks/token-usage");
      if (!response.ok) throw new Error("Failed to fetch token usage");
      return response.json();
    }
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Bookmark Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div>
              <Progress value={health?.percentage || 0} className="h-2" />
              <p className="text-xs text-muted-foreground mt-1">
                {health?.healthy || 0} of {health?.total || 0} bookmarks are healthy ({health?.percentage || 0}%)
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p>Processing Status:</p>
                <ul className="text-xs text-muted-foreground">
                  <li>✓ Processed: {health?.processed || 0}</li>
                  <li>⚠ Failed: {health?.failed || 0}</li>
                  <li>⏳ Unanalyzed: {health?.unanalyzed || 0}</li>
                </ul>
              </div>
              <div>
                <p>Quality Status:</p>
                <ul className="text-xs text-muted-foreground">
                  <li>✓ High Quality: {health?.healthy || 0}</li>
                  <li>⚠ Low Quality: {health?.lowQuality || 0}</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Token Usage Meter */}
      <TokenUsageMeter 
        usedTokens={tokenUsage?.used || 0}
        totalTokens={tokenUsage?.total || 100000}
        isLoading={!tokenUsage && !tokenError}
        error={tokenError?.message}
      />
    </div>
  );
};