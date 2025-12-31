import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import { PipelineActivityPage } from './pages/PipelineActivityPage'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/activity" element={<PipelineActivityPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
