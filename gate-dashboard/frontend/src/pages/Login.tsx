import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { cn } from '../utils/helpers'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card'
import { Eye, EyeOff, Loader2, Lock, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register } = useAuth()

  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const from = (location.state as any)?.from?.pathname || '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      if (isLogin) {
        await login(username, password)
        toast.success('Selamat datang kembali!')
      } else {
        await register({ username, email, password, full_name: fullName })
        toast.success('Akun berhasil dibuat!')
      }
      navigate(from, { replace: true })
    } catch (error: any) {
      const status = error.response?.status
      const detail = error.response?.data?.detail
      const unreachable = !error.response || status === 502 || error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED'

      if (unreachable) {
        // Interceptor already toasted the API-down message
      } else if (status === 401) {
        toast.error('Nama pengguna atau kata sandi salah')
      } else if (status === 400) {
        // Interceptor already toasted FastAPI validation detail
      } else if (status !== 403) {
        toast.error(typeof detail === 'string' ? detail : 'Autentikasi gagal')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background lg:flex-row">
      {/* Branding panel */}
      <aside className="flex flex-col justify-center gap-8 border-b-2 border-ink bg-nb-yellow p-8 text-ink lg:w-5/12 lg:border-b-0 lg:border-r-2 lg:p-12">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md border-2 border-ink bg-nb-yellow shadow-nb">
            <Lock className="h-8 w-8 text-ink" strokeWidth={3} aria-hidden="true" />
          </div>
          <div className="leading-none">
            <p className="text-3xl font-extrabold uppercase tracking-tight text-ink">Gate</p>
            <p className="nb-label mt-2 text-ink">Dashboard</p>
          </div>
        </div>

        <div className="hidden lg:block">
          <p className="text-2xl font-extrabold uppercase leading-tight tracking-tight text-ink">
            Kontrol akses gerbang yang ketat dan aman
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <span className="nb-label rounded-md border-2 border-ink bg-card px-3 py-1.5 text-ink">RFID</span>
            <span className="nb-label rounded-md border-2 border-ink bg-nb-cyan px-3 py-1.5 text-ink">ANPR</span>
            <span className="nb-label rounded-md border-2 border-ink bg-nb-green px-3 py-1.5 text-ink">Manual</span>
          </div>
        </div>

        <div className="nb-stripes hidden items-center gap-3 rounded-md border-2 border-ink bg-card p-4 lg:flex">
          <ShieldCheck className="h-6 w-6 shrink-0 text-ink" strokeWidth={3} aria-hidden="true" />
          <p className="text-sm font-bold text-ink">
            Setiap akses tercatat, diberi stempel waktu, dan terikat pada peran.
          </p>
        </div>
      </aside>

      {/* Form panel */}
      <main className="flex flex-1 items-center justify-center bg-background p-6 sm:p-10">
        <Card className="w-full max-w-md overflow-hidden shadow-nb-lg">
          <div
            className={cn(
              'h-3 w-full border-b-2 border-ink',
              isLogin ? 'bg-nb-yellow' : 'bg-nb-green'
            )}
            aria-hidden="true"
          />

          <CardHeader className="items-center pb-2 text-center">
            <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-md border-2 border-ink bg-nb-yellow shadow-nb lg:hidden">
              <Lock className="h-8 w-8 text-ink" strokeWidth={3} aria-hidden="true" />
            </div>
            <CardTitle className="text-4xl font-extrabold uppercase tracking-tight">
              Gate Dashboard
            </CardTitle>
            <CardDescription className="mt-2 text-sm font-semibold text-muted-foreground">
              {isLogin
                ? 'Masuk ke akun Anda'
                : 'Buat akun — pengguna pertama menjadi admin'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="fullName">Nama Lengkap</Label>
                  <Input
                    id="fullName"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Budi Santoso"
                    required={!isLogin}
                  />
                </div>
              )}
              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="john@example.com"
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="username">Nama Pengguna</Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="budisan"
                  required
                  autoComplete="username"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Kata Sandi</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoComplete={isLogin ? 'current-password' : 'new-password'}
                    className="pr-12"
                  />
                  {/* The toggle sits *inside* the input's box, so it gets no
                      offset shadow — a hard shadow here collides with the
                      input's own right border and reads as a stray block. */}
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'}
                    aria-pressed={showPassword}
                    className="nb-press absolute right-1.5 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md border-2 border-ink bg-muted text-ink"
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" strokeWidth={2.5} aria-hidden="true" />
                    ) : (
                      <Eye className="h-5 w-5" strokeWidth={2.5} aria-hidden="true" />
                    )}
                  </button>
                </div>
              </div>

              <Button type="submit" size="lg" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" strokeWidth={3} />
                    {isLogin ? 'Memproses...' : 'Membuat akun...'}
                  </>
                ) : (
                  isLogin ? 'Masuk' : 'Buat Akun'
                )}
              </Button>
            </form>

            {isLogin && (
              <p className="mt-6 text-center text-sm font-semibold text-muted-foreground">
                Baru pertama kali? Daftar — akun pertama menjadi admin.
              </p>
            )}

            {isLogin && import.meta.env.DEV && (
              <div className="nb-stripes mt-4 rounded-md border-2 border-ink bg-muted p-3 text-center">
                <p className="nb-label text-foreground">Kredensial Dev</p>
                <p className="mt-2 text-sm font-bold text-foreground">
                  <span className="font-mono">admin</span>
                  <span className="mx-1 text-muted-foreground">/</span>
                  <span className="font-mono">admin1234</span>
                </p>
              </div>
            )}

            <div className="mt-6 border-t-2 border-ink pt-5 text-center text-sm font-semibold text-muted-foreground">
              {isLogin ? (
                <>
                  Belum punya akun?{' '}
                  <button
                    type="button"
                    onClick={() => setIsLogin(false)}
                    className="nb-label inline-block rounded-sm px-1 text-ink underline decoration-2 underline-offset-4 hover:bg-nb-yellow"
                  >
                    Daftar
                  </button>
                </>
              ) : (
                <>
                  Sudah punya akun?{' '}
                  <button
                    type="button"
                    onClick={() => setIsLogin(true)}
                    className="nb-label inline-block rounded-sm px-1 text-ink underline decoration-2 underline-offset-4 hover:bg-nb-yellow"
                  >
                    Masuk
                  </button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
