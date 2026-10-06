import { useRef, useState } from 'react'
import { MAX_UPLOAD_MB, uploadPdf } from '../api'

function UploadPanel({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successInfo, setSuccessInfo] = useState(null)
  const requestIdRef = useRef(0)

  const handleFileChange = (e) => {
    const file = e.target.files?.[0] || null
    setSelectedFile(file)
    setError(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a PDF file first.')
      return
    }

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed.')
      return
    }

    const maxBytes = MAX_UPLOAD_MB * 1024 * 1024
    if (selectedFile.size > maxBytes) {
      setError(`File is too large. Maximum size is ${MAX_UPLOAD_MB} MB.`)
      return
    }

    const reqId = ++requestIdRef.current
    setLoading(true)
    setError(null)
    setSuccessInfo(null)

    try {
      const data = await uploadPdf(selectedFile)
      if (reqId !== requestIdRef.current) return

      const info = {
        fileName: selectedFile.name,
        pages: data.pages,
        chunks: data.chunks,
      }
      setSuccessInfo(info)
      if (onUploadSuccess) {
        onUploadSuccess(info)
      }
    } catch (err) {
      if (reqId !== requestIdRef.current) return
      setError(err.message)
    } finally {
      if (reqId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }

  return (
    <section className="panel" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload PDF</h2>
      <div className="upload-controls">
        <label htmlFor="pdf-file-input" className="file-input-label">
          Choose a PDF file to study:
        </label>
        <div className="input-group">
          <input
            id="pdf-file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={loading}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={loading}
          >
            {loading ? 'Processing PDF...' : 'Upload'}
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="alert alert-error">
          {error}
        </div>
      )}

      {successInfo && (
        <div className="alert alert-success">
          <p className="success-text">
            <strong>{successInfo.fileName}</strong> is ready ({successInfo.pages} pages, {successInfo.chunks} chunks)
          </p>
          <p className="note-text">
            Uploading a new PDF replaces the previous document.
          </p>
        </div>
      )}
    </section>
  )
}

export default UploadPanel
