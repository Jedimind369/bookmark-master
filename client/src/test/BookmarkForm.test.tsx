
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BookmarkForm } from '../components/organisms/BookmarkForm';

describe('BookmarkForm', () => {
  it('renders correctly with empty initial data', () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    
    render(<BookmarkForm onSubmit={onSubmit} onCancel={onCancel} />);
    
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/url/i)).toBeInTheDocument();
  });

  it('handles form submission correctly', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    
    render(<BookmarkForm onSubmit={onSubmit} onCancel={onCancel} />);
    
    fireEvent.change(screen.getByLabelText(/url/i), {
      target: { value: 'https://example.com' },
    });
    
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    
    expect(onSubmit).toHaveBeenCalled();
  });
});
