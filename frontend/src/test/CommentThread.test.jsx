import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CommentThread from '../components/CommentThread'

describe('CommentThread', () => {
  it('renders existing comments', () => {
    const comments = [
      { id: 1, body: 'Nice change!', author: { username: 'alice' }, is_resolved: false, created_at: '2025-01-01T00:00:00Z' },
    ]
    render(<CommentThread comments={comments} linePosition={1} />)
    expect(screen.getByText('Nice change!')).toBeInTheDocument()
    expect(screen.getByText('alice')).toBeInTheDocument()
  })

  it('submits a new comment', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<CommentThread comments={[]} linePosition={5} onSubmit={onSubmit} />)

    await user.type(screen.getByPlaceholderText('Add a comment...'), 'Looks good')
    await user.click(screen.getByText('Comment'))

    expect(onSubmit).toHaveBeenCalledWith({
      body: 'Looks good',
      line_position: 5,
      parent: null,
    })
  })

  it('does not submit empty comment', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<CommentThread comments={[]} linePosition={1} onSubmit={onSubmit} />)

    await user.click(screen.getByText('Comment'))
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
