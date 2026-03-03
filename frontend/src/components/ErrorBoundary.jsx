import { Component } from 'react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[60vh] flex items-center justify-center bg-slate-50 px-4">
          <div className="max-w-md text-center">
            <h1 className="text-lg font-semibold text-bharat-navy mb-2">
              Something went wrong loading the dashboard.
            </h1>
            <p className="text-sm text-slate-600">
              Please refresh the page or try again in a moment.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary

