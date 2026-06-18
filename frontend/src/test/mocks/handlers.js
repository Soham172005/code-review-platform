import { http, HttpResponse } from 'msw'

export const handlers = [
  http.post('/api/token/', async ({ request }) => {
    const body = await request.json()
    if (body.username === 'testuser' && body.password === 'testpass') {
      return HttpResponse.json({
        access: 'fake-access-token',
        refresh: 'fake-refresh-token',
      })
    }
    return HttpResponse.json(
      { detail: 'No active account found with the given credentials' },
      { status: 401 }
    )
  }),

  http.get('/api/users/me/', () => {
    return HttpResponse.json({
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      role: 'author',
    })
  }),

  http.post('/api/users/register/', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json(
      { id: 1, username: body.username, email: body.email },
      { status: 201 }
    )
  }),

  http.get('/api/repos/', () => {
    return HttpResponse.json({
      results: [
        { id: 1, name: 'test-repo', owner: { username: 'testuser' }, github_url: '', created_at: '2025-01-01T00:00:00Z' },
      ],
    })
  }),

  http.get('/api/prs/:id/diff/', () => {
    return HttpResponse.json([
      {
        sha: 'abc123',
        diff_files: [
          {
            id: 1,
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
                    { content: 'unchanged', line_type: 'context', old_lineno: 3, new_lineno: 3 },
                  ],
                },
              ],
            },
          },
        ],
      },
    ])
  }),
]
