import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface TokenUsageProps {
  usedTokens: number;
  totalTokens: number;
  isLoading?: boolean;
  error?: string;
}

export function TokenUsageMeter({ 
  usedTokens, 
  totalTokens, 
  isLoading = false,
  error
}: TokenUsageProps) {
  const percentage = Math.min(100, Math.round((usedTokens / totalTokens) * 100));
  const remaining = totalTokens - usedTokens;
  const isWarning = percentage > 80;
  const isCritical = percentage > 95;

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Token Usage</h3>
        <span className={`text-sm font-medium ${
          isCritical ? 'text-destructive' : 
          isWarning ? 'text-yellow-500' : 
          'text-muted-foreground'
        }`}>
          {usedTokens.toLocaleString()} / {totalTokens.toLocaleString()}
        </span>
      </div>

      <Progress 
        value={percentage} 
        className={`h-2 ${
          isCritical ? 'bg-destructive/20' : 
          isWarning ? 'bg-yellow-100' : 
          'bg-secondary'
        }`}
      />

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {remaining.toLocaleString()} tokens remaining
        </span>
        <span>
          {percentage}% used
        </span>
      </div>

      {error && (
        <Alert variant="destructive" className="mt-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Changed warning alert to use default variant with custom styling */}
      {isWarning && !isCritical && (
        <Alert className="mt-2 border-yellow-500 text-yellow-500">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Token usage is high. Consider clearing some analyzed content.
          </AlertDescription>
        </Alert>
      )}

      {isCritical && (
        <Alert variant="destructive" className="mt-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Critical token usage! Analysis of new content may be limited.
          </AlertDescription>
        </Alert>
      )}
    </Card>
  );
}