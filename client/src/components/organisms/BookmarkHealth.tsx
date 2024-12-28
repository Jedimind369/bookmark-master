
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
        <div className="flex flex-col gap-2">
          <Progress value={health?.percentage || 0} className="h-2" />
          <p className="text-xs text-muted-foreground">
            {health?.healthy || 0} of {health?.total || 0} bookmarks are healthy ({health?.percentage || 0}%)
          </p>
        </div>
      </CardContent>
    </Card>
  );
};
