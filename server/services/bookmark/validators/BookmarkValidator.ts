import { ValidationResult, Bookmark } from '../../../interfaces/services';

export abstract class BookmarkValidator {
    abstract validate(bookmark: Bookmark): ValidationResult;
    
    protected validateUrl(url: string): boolean {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    protected validateTitle(title?: string): boolean {
        return !title || (title.length >= 1 && title.length <= 200);
    }

    protected validateDescription(description?: string): boolean {
        return !description || (description.length >= 1 && description.length <= 1000);
    }

    protected validateTags(tags?: string[]): boolean {
        return !tags || (
            tags.length <= 20 && 
            tags.every(tag => tag.length >= 1 && tag.length <= 50)
        );
    }
}

export class UrlValidator extends BookmarkValidator {
    validate(bookmark: Bookmark): ValidationResult {
        const errors: string[] = [];
        
        if (!this.validateUrl(bookmark.url)) {
            errors.push('Invalid URL format');
        }
        
        if (!this.validateTitle(bookmark.title)) {
            errors.push('Title must be between 1 and 200 characters');
        }
        
        if (!this.validateDescription(bookmark.description)) {
            errors.push('Description must be between 1 and 1000 characters');
        }
        
        if (!this.validateTags(bookmark.tags)) {
            errors.push('Tags must be between 1 and 50 characters each, with a maximum of 20 tags');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }
} 