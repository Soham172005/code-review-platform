import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from '../context/AuthContext'
import LoginPage from '../pages/LoginPage'

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <LoginPage />
          <Toaster />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

describe('LoginPage', () => {
  it('renders the login form', () => {
    renderLogin()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByText('Sign in')).toBeInTheDocument()
  })

  it('shows error on invalid credentials', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Username'), 'wrong')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByText('Sign in'))

    await waitFor(
      () => {
        const toast = screen.getByText((content) =>
          content.includes('No active account found')
        )
        expect(toast).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })
})
