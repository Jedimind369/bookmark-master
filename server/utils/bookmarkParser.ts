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
    const items = node.getElementsByTagName('dt');
    
    for (const item of Array.from(items)) {
      const link = item.querySelector('a');
      if (link) {
        const url = link.getAttribute('href');
        const title = link.textContent;
        const dateAdded = link.getAttribute('add_date');
        const tags = link.getAttribute('tags')?.split(',').map(tag => tag.trim()) || [];
        
        if (url && title) {
          bookmarks.push({
            url,
            title,
            dateAdded: dateAdded ? new Date(parseInt(dateAdded) * 1000) : undefined,
            tags,
            collections: [...currentPath].filter(Boolean),
          });
        }
      }
      
      // Process folders (DL elements)
      const folder = item.querySelector('h3');
      if (folder) {
        const folderName = folder.textContent;
        const sublist = item.querySelector('dl');
        if (sublist) {
          processNode(sublist, [...currentPath, folderName || '']);
        }
      }
    }
  }

  // Start processing from the root DL element
  const rootList = document.querySelector('dl');
  if (rootList) {
    processNode(rootList);
  }

  return bookmarks;
}
