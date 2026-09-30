import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  allowedRoles?: string[]
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-5 bg-background">
        {/* Chunky square spinner — hard corners, no soft blur */}
        <div className="h-12 w-12 animate-spin rounded-md border-2 border-ink border-t-transparent bg-nb-yellow shadow-nb" />
        <p className="nb-label text-muted-foreground">Memuat…</p>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}