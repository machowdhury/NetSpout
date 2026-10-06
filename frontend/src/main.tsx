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
        <div className="flex items-center justify-center min-h-screen bg-[#f4f6f8] text-[#17212b] p-6 font-sans">
          <div className="max-w-md w-full bg-white border border-[#d9e0e6] rounded-xl p-6 shadow-lg text-center">
            <div className="w-12 h-12 rounded-lg bg-[#fff0ee] border border-[#efbbb5] text-[#b42318] flex items-center justify-center mx-auto mb-4 text-xl">
              ⚠️
            </div>
            <h2 className="text-lg font-bold mb-2">NetSpout workspace unavailable</h2>
            <p className="text-xs text-[#5f6e7c] mb-4">
              The Unified Enterprise Telemetry Lab encountered a rendering error.
            </p>
            <pre className="text-[11px] bg-[#f8fafb] p-3 rounded border border-[#d9e0e6] text-[#b42318] text-left font-mono overflow-auto max-h-32 mb-4">
              {this.state.error?.message || "Unknown error"}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[#066570] hover:bg-[#054f58] text-white text-xs font-semibold rounded-md transition-colors cursor-pointer"
            >
              Reload NetSpout
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
