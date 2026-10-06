import { useRef, useState } from 'react'
import { QUIZ_DEFAULT, QUIZ_MAX, QUIZ_MIN, generateQuiz } from '../api'

function QuizPanel() {
  const [numQuestions, setNumQuestions] = useState(QUIZ_DEFAULT)
  const [questions, setQuestions] = useState([])
  const [userAnswers, setUserAnswers] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const requestIdRef = useRef(0)

  const handleGenerateQuiz = async () => {
    const trimmed = String(numQuestions).trim()
    const parsed = Number(trimmed)
    if (!trimmed || !Number.isInteger(parsed) || parsed < QUIZ_MIN || parsed > QUIZ_MAX) {
      setError(`Number of questions must be an integer between ${QUIZ_MIN} and ${QUIZ_MAX}.`)
      return
    }

    const reqId = ++requestIdRef.current
    setLoading(true)
    setError(null)
    setUserAnswers({})
    setQuestions([])

    try {
      const data = await generateQuiz(parsed)
      if (reqId !== requestIdRef.current) return
      setQuestions(data.questions || [])
    } catch (err) {
      if (reqId !== requestIdRef.current) return
      setError(err.message)
    } finally {
      if (reqId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }

  const handleSelectOption = (qIndex, optIndex) => {
    // If the question is already locked, do nothing
    if (userAnswers[qIndex] !== undefined) return

    setUserAnswers((prev) => ({
      ...prev,
      [qIndex]: optIndex,
    }))
  }

  const answeredQuestionKeys = Object.keys(userAnswers)
  const answeredCount = answeredQuestionKeys.length
  const score = answeredQuestionKeys.reduce((acc, key) => {
    const qIndex = Number(key)
    const chosenIndex = userAnswers[qIndex]
    const correctIndex = questions[qIndex]?.correct_index
    return acc + (chosenIndex === correctIndex ? 1 : 0)
  }, 0)

  return (
    <section className="panel" aria-labelledby="quiz-heading">
      <h2 id="quiz-heading">Self-Study Quiz</h2>

      <div className="quiz-controls">
        <label htmlFor="quiz-count-input" className="form-label">
          Number of questions ({QUIZ_MIN}–{QUIZ_MAX}):
        </label>
        <div className="input-group">
          <input
            id="quiz-count-input"
            type="number"
            min={QUIZ_MIN}
            max={QUIZ_MAX}
            value={numQuestions}
            onChange={(e) => {
              setNumQuestions(e.target.value)
              setError(null)
            }}
            disabled={loading}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleGenerateQuiz}
            disabled={loading}
          >
            {loading ? 'Generating quiz... this can take up to a minute' : 'Generate quiz'}
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="alert alert-error">
          {error}
        </div>
      )}

      {questions.length > 0 && (
        <div className="quiz-content">
          <div className="quiz-score-bar">
            {answeredCount > 0 ? (
              <span className="quiz-score-badge">
                Score: {score} / {questions.length}
              </span>
            ) : (
              <span />
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleGenerateQuiz}
              disabled={loading}
            >
              Try again
            </button>
          </div>

          <div className="questions-list">
            {questions.map((q, qIndex) => {
              const isLocked = userAnswers[qIndex] !== undefined
              const selectedOpt = userAnswers[qIndex]

              return (
                <fieldset key={qIndex} className="quiz-question-fieldset">
                  <legend className="quiz-question-legend">
                    {qIndex + 1}. {q.question}
                  </legend>
                  <div className="quiz-options-list">
                    {q.options.map((opt, optIndex) => {
                      const isSelected = selectedOpt === optIndex
                      const isCorrect = optIndex === q.correct_index

                      let optionStateClass = ''
                      let badge = null

                      if (isLocked) {
                        if (isSelected && isCorrect) {
                          optionStateClass = 'option-correct'
                          badge = <span className="status-badge badge-correct">✓ Correct</span>
                        } else if (isSelected && !isCorrect) {
                          optionStateClass = 'option-incorrect'
                          badge = <span className="status-badge badge-incorrect">✗ Incorrect</span>
                        } else if (!isSelected && isCorrect) {
                          optionStateClass = 'option-highlight-correct'
                          badge = <span className="status-badge badge-highlight">✓ Correct Answer</span>
                        } else {
                          optionStateClass = 'option-muted'
                        }
                      }

                      return (
                        <label
                          key={optIndex}
                          className={`quiz-option-label ${optionStateClass}`}
                        >
                          <input
                            type="radio"
                            name={`quiz-question-${qIndex}`}
                            value={optIndex}
                            checked={isSelected}
                            onChange={() => handleSelectOption(qIndex, optIndex)}
                            disabled={isLocked || loading}
                          />
                          <span className="option-text">{opt}</span>
                          {badge}
                        </label>
                      )
                    })}
                  </div>

                  {isLocked && (
                    <div className="quiz-explanation">
                      <strong>Explanation:</strong> {q.explanation}
                    </div>
                  )}
                </fieldset>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}

export default QuizPanel
