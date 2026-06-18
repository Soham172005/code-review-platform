import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

let accessToken = null
let refreshPromise = null

export function setAccessToken(token) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        if (!refreshPromise) {
          refreshPromise = api.post('/token/refresh/', {}, { _retry: true })
        }
        const res = await refreshPromise
        refreshPromise = null
        accessToken = res.data.access
        original.headers.Authorization = `Bearer ${accessToken}`
        return api(original)
      } catch {
        refreshPromise = null
        accessToken = null
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (username, password) =>
  api.post('/token/', { username, password })

export const register = (username, email, password) =>
  api.post('/users/register/', { username, email, password })

export const logout = (refresh) =>
  api.post('/users/logout/', { refresh })

export const refreshToken = () =>
  api.post('/token/refresh/')

export const getMe = () =>
  api.get('/users/me/')

export const updateMe = (data) =>
  api.patch('/users/me/', data)

// Repos
export const listRepos = (page = 1) =>
  api.get('/repos/', { params: { page } })

export const createRepo = (data) =>
  api.post('/repos/', data)

export const getRepo = (id) =>
  api.get(`/repos/${id}/`)

// Pull Requests
export const listPRs = (repoId, page = 1) =>
  api.get(`/repos/${repoId}/prs/`, { params: { page } })

export const createPR = (repoId, data) =>
  api.post(`/repos/${repoId}/prs/`, data)

export const getPR = (id) =>
  api.get(`/prs/${id}/`)

export const getDiff = (prId) =>
  api.get(`/prs/${prId}/diff/`)

export const transitionPR = (prId, transition) =>
  api.post(`/prs/${prId}/transition/`, { transition })

export const getPRHistory = (prId) =>
  api.get(`/prs/${prId}/history/`)

// Reviews
export const submitReview = (prId, data) =>
  api.post(`/prs/${prId}/reviews/`, data)

export const addComment = (prId, data) =>
  api.post(`/prs/${prId}/comments/`, data)

export const resolveComment = (commentId) =>
  api.post(`/reviews/comments/${commentId}/resolve/`)

export default api
