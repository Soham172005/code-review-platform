import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatusBadge from '../components/StatusBadge'

describe('StatusBadge', () => {
  const statuses = [
    { status: 'draft', label: 'Draft', colorClass: 'bg-gray-100' },
    { status: 'open', label: 'Open', colorClass: 'bg-blue-100' },
    { status: 'in_review', label: 'In Review', colorClass: 'bg-yellow-100' },
    { status: 'approved', label: 'Approved', colorClass: 'bg-green-100' },
    { status: 'merged', label: 'Merged', colorClass: 'bg-purple-100' },
    { status: 'closed', label: 'Closed', colorClass: 'bg-red-100' },
  ]

  statuses.forEach(({ status, label, colorClass }) => {
    it(`renders "${label}" with ${colorClass} for status "${status}"`, () => {
      render(<StatusBadge status={status} />)
      const badge = screen.getByTestId('status-badge')
      expect(badge).toHaveTextContent(label)
      expect(badge.className).toContain(colorClass)
    })
  })
})
