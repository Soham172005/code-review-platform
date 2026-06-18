import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DiffViewer from '../components/DiffViewer'

const sampleDiffFiles = [
  {
    file_path: 'src/main.py',
    change_type: 'modified',
    patch: {
      hunks: [
        {
          old_start: 1,
          old_lines: 3,
          new_start: 1,
          new_lines: 4,
          lines: [
            { content: 'import os', line_type: 'context', old_lineno: 1, new_lineno: 1 },
            { content: 'old_line', line_type: 'removed', old_lineno: 2, new_lineno: null },
            { content: 'new_line', line_type: 'added', old_lineno: null, new_lineno: 2 },
          ],
        },
      ],
    },
  },
]

describe('DiffViewer', () => {
  it('renders the diff viewer container', () => {
    render(<DiffViewer diffFiles={sampleDiffFiles} />)
    expect(screen.getByTestId('diff-viewer')).toBeInTheDocument()
  })

  it('renders the file path', () => {
    render(<DiffViewer diffFiles={sampleDiffFiles} />)
    expect(screen.getByText('src/main.py')).toBeInTheDocument()
  })

  it('renders added lines with correct test id', () => {
    render(<DiffViewer diffFiles={sampleDiffFiles} />)
    const addedLines = screen.getAllByTestId('diff-line-added')
    expect(addedLines).toHaveLength(1)
  })

  it('renders removed lines with correct test id', () => {
    render(<DiffViewer diffFiles={sampleDiffFiles} />)
    const removedLines = screen.getAllByTestId('diff-line-removed')
    expect(removedLines).toHaveLength(1)
  })

  it('renders context lines with correct test id', () => {
    render(<DiffViewer diffFiles={sampleDiffFiles} />)
    const contextLines = screen.getAllByTestId('diff-line-context')
    expect(contextLines).toHaveLength(1)
  })

  it('renders with empty diff files', () => {
    render(<DiffViewer diffFiles={[]} />)
    expect(screen.getByTestId('diff-viewer')).toBeInTheDocument()
  })
})
