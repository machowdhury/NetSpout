import { StrictMode, Component } from "react"
import type { ErrorInfo, ReactNode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("NetSpout Uncaught Error:", error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-[#0B0F19] text-slate-100 p-6 font-sans">
          <div className="max-w-md w-full bg-[#1F2937] border border-[#374151] rounded-xl p-6 shadow-2xl text-center">
            <div className="w-12 h-12 rounded-full bg-[#EF4444]/20 border border-[#EF4444]/40 text-[#EF4444] flex items-center justify-center mx-auto mb-4 text-xl">
              ⚠️
            </div>
            <h2 className="text-lg font-bold text-white mb-2">NetSpout Canvas Alert</h2>
            <p className="text-xs text-slate-400 mb-4">
              A UI rendering exception occurred. You can restore the baseline workspace safely:
            </p>
            <pre className="text-[11px] bg-[#0B0F19] p-3 rounded border border-[#374151] text-[#EF4444] text-left font-mono overflow-auto max-h-32 mb-4">
              {this.state.error?.message || "Unknown error"}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white text-xs font-semibold rounded-lg transition-all shadow-lg cursor-pointer"
            >
              Reload NetSpout Canvas
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
