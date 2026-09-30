import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { GateProvider } from './context/GateContext'
import { Layout } from './components/layout/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Tickets } from './pages/Tickets'
import { RFID } from './pages/RFID'
import { Passages } from './pages/Passages'
import { Settings } from './pages/Settings'
import { ProtectedRoute } from './components/auth/ProtectedRoute'

function App() {
  return (
    <AuthProvider>
      <GateProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="tickets" element={<Tickets />} />
            <Route path="rfid" element={<RFID />} />
            <Route path="passages" element={<Passages />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </GateProvider>
    </AuthProvider>
  )
}

export default App