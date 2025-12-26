import { useState, useCallback, useRef } from 'react'

interface Card {
  id: number
  x: number
  y: number
  width: number
  height: number
}

interface ProcessResult {
  success: boolean
  cards_detected: number
  cards: Card[]
  processed_image: string
  svg_cut_file: string
  image_dimensions: {
    width_px: number
    height_px: number
    width_mm: number
    height_mm: number
  }
}

interface PreviewResult {
  success: boolean
  cards_detected: number
  cards: Card[]
  preview_image: string
}

type ProcessingStep = 'idle' | 'uploading' | 'detecting' | 'processing' | 'done' | 'error'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [detectionPreview, setDetectionPreview] = useState<string | null>(null)
  const [processedResult, setProcessedResult] = useState<ProcessResult | null>(null)
  const [step, setStep] = useState<ProcessingStep>('idle')
  const [error, setError] = useState<string | null>(null)

  // Settings
  const [gridCols, setGridCols] = useState(3)
  const [gridRows, setGridRows] = useState(3)
  const [autoDetect, setAutoDetect] = useState(true)
  const [dpi, setDpi] = useState(300)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback((selectedFile: File) => {
    setFile(selectedFile)
    setPreviewUrl(URL.createObjectURL(selectedFile))
    setDetectionPreview(null)
    setProcessedResult(null)
    setStep('idle')
    setError(null)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      handleFileSelect(selectedFile)
    }
  }, [handleFileSelect])

  const previewDetection = async () => {
    if (!file) return

    setStep('detecting')
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(
        `/api/preview?grid_cols=${gridCols}&grid_rows=${gridRows}&auto_detect=${autoDetect}&dpi=${dpi}`,
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Preview failed')
      }

      const result: PreviewResult = await response.json()
      setDetectionPreview(result.preview_image)
      setStep('idle')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
      setStep('error')
    }
  }

  const processImage = async () => {
    if (!file) return

    setStep('processing')
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(
        `/api/process?grid_cols=${gridCols}&grid_rows=${gridRows}&auto_detect=${autoDetect}&dpi=${dpi}`,
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Processing failed')
      }

      const result: ProcessResult = await response.json()
      setProcessedResult(result)
      setStep('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed')
      setStep('error')
    }
  }

  const downloadProcessedImage = () => {
    if (!processedResult) return

    const link = document.createElement('a')
    link.href = processedResult.processed_image
    link.download = 'mtg-proxies-rounded.png'
    link.click()
  }

  const downloadSVG = () => {
    if (!processedResult) return

    const blob = new Blob([processedResult.svg_cut_file], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'mtg-proxies-cutfile.svg'
    link.click()
    URL.revokeObjectURL(url)
  }

  const resetAll = () => {
    setFile(null)
    setPreviewUrl(null)
    setDetectionPreview(null)
    setProcessedResult(null)
    setStep('idle')
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            MTG Proxy Cutter
          </h1>
          <p className="text-gray-400">
            Process card sheets for Silhouette Portrait 4 print-and-cut
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Upload & Settings */}
          <div className="space-y-6">
            {/* Upload Area */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
                ${file ? 'border-green-500 bg-green-500/10' : 'border-gray-600 hover:border-gray-500 hover:bg-gray-800/50'}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileInputChange}
                className="hidden"
              />
              {file ? (
                <div>
                  <svg className="w-12 h-12 mx-auto mb-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <p className="text-green-400 font-medium">{file.name}</p>
                  <p className="text-gray-500 text-sm mt-1">Click to change</p>
                </div>
              ) : (
                <div>
                  <svg className="w-12 h-12 mx-auto mb-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="text-gray-400">Drop your card sheet image here</p>
                  <p className="text-gray-500 text-sm mt-1">or click to browse</p>
                </div>
              )}
            </div>

            {/* Settings Panel */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 text-white">Settings</h2>

              <div className="space-y-4">
                {/* Auto Detect Toggle */}
                <div className="flex items-center justify-between">
                  <label className="text-gray-300">Auto-detect cards</label>
                  <button
                    onClick={() => setAutoDetect(!autoDetect)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${autoDetect ? 'bg-blue-600' : 'bg-gray-600'}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${autoDetect ? 'translate-x-6' : 'translate-x-1'}`}
                    />
                  </button>
                </div>

                {/* Grid Settings (when auto-detect is off) */}
                {!autoDetect && (
                  <div className="space-y-3 pt-2 border-t border-gray-700">
                    <div>
                      <label className="text-gray-300 text-sm">Columns</label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={gridCols}
                        onChange={(e) => setGridCols(parseInt(e.target.value) || 1)}
                        className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-gray-300 text-sm">Rows</label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={gridRows}
                        onChange={(e) => setGridRows(parseInt(e.target.value) || 1)}
                        className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                      />
                    </div>
                  </div>
                )}

                {/* DPI Setting */}
                <div>
                  <label className="text-gray-300 text-sm">Print DPI</label>
                  <select
                    value={dpi}
                    onChange={(e) => setDpi(parseInt(e.target.value))}
                    className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  >
                    <option value="150">150 DPI</option>
                    <option value="300">300 DPI (Recommended)</option>
                    <option value="600">600 DPI</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              <button
                onClick={previewDetection}
                disabled={!file || step === 'detecting' || step === 'processing'}
                className="w-full py-3 px-4 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500
                  text-white rounded-lg font-medium transition-colors"
              >
                {step === 'detecting' ? 'Detecting...' : 'Preview Detection'}
              </button>

              <button
                onClick={processImage}
                disabled={!file || step === 'detecting' || step === 'processing'}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500
                  text-white rounded-lg font-medium transition-colors"
              >
                {step === 'processing' ? 'Processing...' : 'Process & Generate Cut File'}
              </button>

              {(processedResult || detectionPreview) && (
                <button
                  onClick={resetAll}
                  className="w-full py-2 px-4 bg-red-600/20 hover:bg-red-600/30 text-red-400
                    rounded-lg font-medium transition-colors"
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Center/Right Columns - Preview & Results */}
          <div className="lg:col-span-2 space-y-6">
            {/* Error Display */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 text-red-200">
                <strong>Error:</strong> {error}
              </div>
            )}

            {/* Preview Area */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 text-white">Preview</h2>

              {!previewUrl && !detectionPreview && !processedResult && (
                <div className="aspect-video bg-gray-700 rounded-lg flex items-center justify-center">
                  <p className="text-gray-500">Upload an image to see preview</p>
                </div>
              )}

              {/* Show detection preview if available, otherwise original */}
              {(detectionPreview || previewUrl) && !processedResult && (
                <div className="space-y-4">
                  <img
                    src={detectionPreview || previewUrl || ''}
                    alt="Preview"
                    className="max-w-full rounded-lg border border-gray-600"
                  />
                  {detectionPreview && (
                    <p className="text-sm text-gray-400">
                      Green boxes show detected card boundaries. Red arcs show corner rounding.
                    </p>
                  )}
                </div>
              )}

              {/* Processed Result */}
              {processedResult && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-400 mb-2">Processed Image</h3>
                      <img
                        src={processedResult.processed_image}
                        alt="Processed"
                        className="max-w-full rounded-lg border border-gray-600 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIGZpbGw9IiMzMzMiLz48cmVjdCB4PSIxMCIgeT0iMTAiIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgZmlsbD0iIzMzMyIvPjwvc3ZnPg==')]"
                      />
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-400 mb-2">Cut File Preview</h3>
                      <div
                        className="bg-white rounded-lg p-4 border border-gray-600"
                        dangerouslySetInnerHTML={{
                          __html: processedResult.svg_cut_file.replace(
                            '<svg',
                            '<svg style="width:100%;height:auto"'
                          ),
                        }}
                      />
                    </div>
                  </div>

                  {/* Info */}
                  <div className="bg-gray-700 rounded-lg p-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">Cards Detected</span>
                        <p className="text-white font-medium">{processedResult.cards_detected}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Image Size</span>
                        <p className="text-white font-medium">
                          {processedResult.image_dimensions.width_px} × {processedResult.image_dimensions.height_px} px
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-400">Print Size</span>
                        <p className="text-white font-medium">
                          {processedResult.image_dimensions.width_mm.toFixed(1)} × {processedResult.image_dimensions.height_mm.toFixed(1)} mm
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-400">Corner Radius</span>
                        <p className="text-white font-medium">3mm (MTG Standard)</p>
                      </div>
                    </div>
                  </div>

                  {/* Download Buttons */}
                  <div className="flex gap-4">
                    <button
                      onClick={downloadProcessedImage}
                      className="flex-1 py-3 px-4 bg-green-600 hover:bg-green-500 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Print Image (PNG)
                    </button>
                    <button
                      onClick={downloadSVG}
                      className="flex-1 py-3 px-4 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Cut File (SVG)
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 text-white">How to Use</h2>
              <ol className="list-decimal list-inside space-y-2 text-gray-300">
                <li>Upload your MTG proxy card sheet image (3×3 or other grid)</li>
                <li>Click "Preview Detection" to verify card boundaries are correct</li>
                <li>If auto-detection fails, disable it and set grid size manually</li>
                <li>Click "Process & Generate Cut File" to create outputs</li>
                <li>Download the PNG image for printing</li>
                <li>Download the SVG cut file and import into Silhouette Studio</li>
                <li>Use print-and-cut workflow with registration marks</li>
              </ol>

              <div className="mt-4 p-4 bg-gray-700 rounded-lg">
                <h3 className="font-medium text-yellow-400 mb-2">Silhouette Studio Tips</h3>
                <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                  <li>Import the SVG file first, then place the printed sheet</li>
                  <li>Enable registration mark detection in cut settings</li>
                  <li>Use "Print and Cut" preset for best results</li>
                  <li>Test with a single sheet before batch cutting</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>MTG card dimensions: 63mm × 88mm | Corner radius: 3mm</p>
          <p className="mt-1">Designed for Silhouette Portrait 4</p>
        </footer>
      </div>
    </div>
  )
}
