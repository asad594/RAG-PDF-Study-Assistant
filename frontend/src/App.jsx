import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import AskPanel from './components/AskPanel'
import QuizPanel from './components/QuizPanel'
import './App.css'

function App() {
  const [uploadedDoc, setUploadedDoc] = useState(null)

  const handleUploadSuccess = (docInfo) => {
    setUploadedDoc(docInfo)
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>RAG PDF Study Assistant</h1>
        <p className="app-description">
          Upload study materials in PDF format, ask questions, and test your knowledge with AI-generated quizzes.
        </p>
        {uploadedDoc && (
          <div className="active-doc-badge" aria-live="polite">
            Active document: <strong>{uploadedDoc.fileName}</strong> ({uploadedDoc.pages} pages, {uploadedDoc.chunks} chunks)
          </div>
        )}
      </header>

      <main className="app-main">
        <UploadPanel onUploadSuccess={handleUploadSuccess} />
        <AskPanel />
        <QuizPanel />
      </main>
    </div>
  )
}

export default App
