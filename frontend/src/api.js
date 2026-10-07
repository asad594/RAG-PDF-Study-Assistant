const RAW_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').trim().replace(/\/+$/, '')
const BASE_PATH = RAW_URL ? (RAW_URL.endsWith('/api') ? RAW_URL : `${RAW_URL}/api`) : '/api'

export const REQUEST_TIMEOUT_MS = 120000
export const MAX_UPLOAD_MB = 10
export const QUIZ_MIN = 1
export const QUIZ_MAX = 10
export const QUIZ_DEFAULT = 5

async function request(endpoint, options = {}) {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, REQUEST_TIMEOUT_MS)

  try {
    let response
    try {
      response = await fetch(`${BASE_PATH}${endpoint}`, {
        ...options,
        signal: controller.signal,
      })
    } catch {
      if (timedOut) {
        throw new Error('The request took too long. Please try again.')
      }
      throw new Error('Cannot reach the server. Make sure the backend is running.')
    }

    let data = null
    try {
      const text = await response.text()
      if (text) {
        try {
          data = JSON.parse(text)
        } catch {
          data = null
        }
      }
    } catch {
      if (timedOut) {
        throw new Error('The request took too long. Please try again.')
      }
      throw new Error('Cannot reach the server. Make sure the backend is running.')
    }

    if (!response.ok) {
      const message =
        (data && typeof data.error === 'string' && data.error.trim()) ||
        (data && typeof data.detail === 'string' && data.detail.trim()) ||
        'Something went wrong. Please try again.'
      throw new Error(message)
    }

    return data
  } finally {
    clearTimeout(timer)
  }
}

export async function uploadPdf(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/upload/', {
    method: 'POST',
    body: formData,
  })
}

export async function askQuestion(question) {
  return request('/ask/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  })
}

export async function generateQuiz(numQuestions = QUIZ_DEFAULT) {
  return request('/quiz/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ num_questions: numQuestions }),
  })
}
