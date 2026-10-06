import { useRef, useState } from 'react'
import { askQuestion } from '../api'

function SourceItem({ page, text }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const isLong = Boolean(text && text.length > 200)

  return (
    <li className="source-item">
      <div className="source-item-header">
        <span className="source-page-tag">Page {page}</span>
        {isLong && (
          <button
            type="button"
            className="btn-text"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
          >
            {isExpanded ? 'Show less' : 'Show full chunk'}
          </button>
        )}
      </div>
      <p className={`source-chunk-text ${!isExpanded && isLong ? 'clamped' : ''}`}>
        {text}
      </p>
    </li>
  )
}

function AskPanel() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [answerData, setAnswerData] = useState(null)
  const [showSources, setShowSources] = useState(false)
  const requestIdRef = useRef(0)

  const handleAsk = async () => {
    if (loading) return

    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      setError('Please enter a question before asking.')
      return
    }

    const reqId = ++requestIdRef.current
    setLoading(true)
    setError(null)
    setAnswerData(null)
    setShowSources(false)

    try {
      const data = await askQuestion(trimmedQuestion)
      if (reqId !== requestIdRef.current) return
      setAnswerData(data)
      setShowSources(false)
    } catch (err) {
      if (reqId !== requestIdRef.current) return
      setError(err.message)
    } finally {
      if (reqId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleAsk()
    }
  }

  return (
    <section className="panel" aria-labelledby="ask-heading">
      <h2 id="ask-heading">Ask a Question</h2>
      <div className="ask-controls">
        <label htmlFor="ask-question-input" className="form-label">
          Ask anything about the uploaded PDF:
        </label>
        <textarea
          id="ask-question-input"
          className="question-textarea"
          rows={3}
          value={question}
          onChange={(e) => {
            setQuestion(e.target.value)
            setError(null)
          }}
          onKeyDown={handleKeyDown}
          placeholder="e.g. What are the key takeaways from chapter 3?"
          disabled={loading}
        />
        <div className="actions-row">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAsk}
            disabled={loading}
          >
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="alert alert-error">
          {error}
        </div>
      )}

      {answerData && (
        <div className="answer-section">
          <h3 className="answer-heading">Answer</h3>
          <p className="answer-text">{answerData.answer}</p>

          {answerData.sources && answerData.sources.length > 0 && (
            <div className="sources-section">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowSources((prev) => !prev)}
                aria-expanded={showSources}
              >
                {showSources
                  ? 'Hide sources'
                  : `Show sources (${answerData.sources.length})`}
              </button>

              {showSources && (
                <ul className="sources-list">
                  {answerData.sources.map((src, index) => (
                    <SourceItem key={index} page={src.page} text={src.text} />
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default AskPanel
