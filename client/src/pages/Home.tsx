import { useState } from "react";
import { BookmarkList } from "@/components/organisms/BookmarkList";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export function Home() {
  const [isAddingBookmark, setIsAddingBookmark] = useState(false);

  return (
    <div className="container mx-auto p-4 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
          Bookmark Manager
        </h1>
        <Button onClick={() => setIsAddingBookmark(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Bookmark
        </Button>
      </div>

      <BookmarkList 
        isAddingBookmark={isAddingBookmark}
        onAddBookmark={() => setIsAddingBookmark(true)}
        onCancelAdd={() => setIsAddingBookmark(false)}
      />
    </div>
  );
}

export default Home;