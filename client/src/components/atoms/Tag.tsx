import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";

interface TagProps {
  text: string;
  onRemove?: () => void;
}

export const Tag = ({ text, onRemove }: TagProps) => {
  return (
    <Badge variant="secondary" className="flex items-center gap-1">
      {text}
      {onRemove && (
        <X
          className="h-3 w-3 cursor-pointer hover:text-destructive"
          onClick={onRemove}
        />
      )}
    </Badge>
  );
};
