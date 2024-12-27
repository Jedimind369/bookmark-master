import { JSDOM } from 'jsdom';

export interface ParsedBookmark {
  url: string;
  title: string;
  dateAdded?: Date;
  tags: string[];
  collections: string[];
}

export function parseHtmlBookmarks(html: string): ParsedBookmark[] {
  const dom = new JSDOM(html);
  const document = dom.window.document;
  const bookmarks: ParsedBookmark[] = [];

  function processNode(node: Element, currentPath: string[] = []) {
    // Process all DT elements (bookmark items)
    const items = node.querySelectorAll('dt');

    for (const item of Array.from(items)) {
      const link = item.querySelector('a');
      if (link) {
        const url = link.getAttribute('href');
        const title = link.textContent;
        const dateAdded = link.getAttribute('add_date');
        const tags = link.getAttribute('tags')?.split(',').map(tag => tag.trim()).filter(Boolean) || [];

        if (url && title) {
          try {
            // Validate URL
            new URL(url);

            // Get the folder path (collections)
            const folderElements = Array.from(item.closest('dl')?.querySelectorAll(':scope > dt > h3') || []);
            const parentFolders = folderElements.map(el => el.textContent?.trim() || '').filter(Boolean);

            bookmarks.push({
              url,
              title: title.trim(),
              dateAdded: dateAdded ? new Date(parseInt(dateAdded) * 1000) : undefined,
              tags,
              collections: [...currentPath, ...parentFolders].filter(Boolean),
            });
          } catch (error) {
            console.warn(`Skipping invalid URL: ${url}`);
            continue;
          }
        }
      }

      // Process folders (DL elements)
      const folder = item.querySelector('h3');
      if (folder && folder.textContent) {
        const folderName = folder.textContent.trim();
        const sublist = item.querySelector('dl');
        if (sublist) {
          processNode(sublist, [...currentPath, folderName]);
        }
      }
    }
  }

  try {
    // Start processing from the root DL element
    const rootList = document.querySelector('dl');
    if (rootList) {
      processNode(rootList);
    }

    console.log(`Successfully parsed ${bookmarks.length} bookmarks`);
    return bookmarks;
  } catch (error) {
    console.error('Error parsing bookmarks:', error);
    throw new Error(`Failed to parse bookmarks: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}