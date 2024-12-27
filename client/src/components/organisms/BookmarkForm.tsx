import React from "react";
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
import { X } from "lucide-react";

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
                <Input {...field} placeholder="https://example.com" />
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
          <Button type="submit">
            {initialData ? "Update" : "Create"} Bookmark
          </Button>
        </div>
      </form>
    </Form>
  );
};