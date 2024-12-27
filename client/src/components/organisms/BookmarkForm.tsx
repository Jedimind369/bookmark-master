import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tag } from "../atoms/Tag";
import { CreateBookmarkDto, UpdateBookmarkDto } from "@/types/bookmark";
import { Loader2, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const bookmarkSchema = z.object({
  url: z.string().url(),
  title: z.string().min(1),
  description: z.string().optional(),
  tags: z.array(z.string()),
  collections: z.array(z.string()),
});

interface BookmarkFormProps {
  initialData?: UpdateBookmarkDto;
  onSubmit: (data: CreateBookmarkDto | UpdateBookmarkDto) => void;
  onCancel: () => void;
}

export const BookmarkForm = ({ initialData, onSubmit, onCancel }: BookmarkFormProps) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { toast } = useToast();

  const form = useForm<z.infer<typeof bookmarkSchema>>({
    resolver: zodResolver(bookmarkSchema),
    defaultValues: {
      url: initialData?.url || "",
      title: initialData?.title || "",
      description: initialData?.description || "",
      tags: initialData?.tags || [],
      collections: initialData?.collections || [],
    },
  });

  const analyzeUrl = async (url: string) => {
    try {
      setIsAnalyzing(true);
      const response = await fetch("/api/analyze-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error("Failed to analyze URL");
      }

      const analysis = await response.json();
      form.setValue("title", analysis.title);
      form.setValue("description", analysis.description);
      form.setValue("tags", analysis.tags);

      toast({
        title: "URL Analyzed",
        description: "Title, description, and tags have been automatically generated.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to analyze URL. Please enter details manually.",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUrlChange = async (event: React.FocusEvent<HTMLInputElement>) => {
    const url = event.target.value;
    if (url && url !== initialData?.url) {
      try {
        new URL(url); // Validate URL format
        await analyzeUrl(url);
      } catch (error) {
        // Invalid URL format, skip analysis
      }
    }
  };

  const handleAddTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && e.currentTarget.value) {
      e.preventDefault();
      const newTag = e.currentTarget.value.trim();
      if (!form.getValues().tags.includes(newTag)) {
        form.setValue("tags", [...form.getValues().tags, newTag]);
      }
      e.currentTarget.value = "";
    }
  };

  const handleFormSubmit = (data: z.infer<typeof bookmarkSchema>) => {
    if (initialData?.id) {
      onSubmit({ ...data, id: initialData.id });
    } else {
      onSubmit(data);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleFormSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="url"
          render={({ field }) => (
            <FormItem>
              <FormLabel>URL</FormLabel>
              <FormControl>
                <div className="relative">
                  <Input 
                    {...field} 
                    placeholder="https://example.com" 
                    onBlur={handleUrlChange}
                  />
                  {isAnalyzing && (
                    <div className="absolute right-3 top-2">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  )}
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Title</FormLabel>
              <FormControl>
                <Input {...field} placeholder="Website Title" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea {...field} placeholder="Add a description..." />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="tags"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tags</FormLabel>
              <FormControl>
                <div className="space-y-2">
                  <Input
                    placeholder="Press Enter to add tags"
                    onKeyDown={handleAddTag}
                  />
                  <div className="flex flex-wrap gap-2">
                    {field.value.map((tag) => (
                      <Tag
                        key={tag}
                        text={tag}
                        onRemove={() => {
                          form.setValue(
                            "tags",
                            field.value.filter((t) => t !== tag)
                          );
                        }}
                      />
                    ))}
                  </div>
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isAnalyzing}>
            {initialData ? "Update" : "Create"} Bookmark
          </Button>
        </div>
      </form>
    </Form>
  );
};