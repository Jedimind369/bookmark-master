import { Switch, Route } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/providers/theme";
import { BookmarkProvider } from "@/components/providers/bookmark";
import { Home } from "@/pages/Home";

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BookmarkProvider>
          <div className="min-h-screen bg-background">
            <Switch>
              <Route path="/" component={Home} />
            </Switch>
            <Toaster />
          </div>
        </BookmarkProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;