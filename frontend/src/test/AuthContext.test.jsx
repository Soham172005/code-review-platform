import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../context/AuthContext'

function TestConsumer() {
  const { user, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="user">{user ? user.username : 'none'}</span>
      <button onClick={() => login('testuser', 'testpass')}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  )
}

describe('AuthContext', () => {
  it('starts with no user', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('sets user after login', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )
    await act(async () => {
      screen.getByText('login').click()
    })
    expect(screen.getByTestId('user')).toHaveTextContent('testuser')
  })

  it('clears user after logout', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )
    await act(async () => {
      screen.getByText('login').click()
    })
    expect(screen.getByTestId('user')).toHaveTextContent('testuser')

    act(() => {
      screen.getByText('logout').click()
    })
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })
})
