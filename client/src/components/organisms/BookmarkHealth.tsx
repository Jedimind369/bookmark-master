
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export const BookmarkHealth = () => {
  const { data: health } = useQuery({
    queryKey: ["/api/bookmarks/health"],
    queryFn: async () => {
      const response = await fetch("/api/bookmarks/health");
      if (!response.ok) throw new Error("Failed to fetch health status");
      return response.json();
    }
  });

  return (
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
  );
};
