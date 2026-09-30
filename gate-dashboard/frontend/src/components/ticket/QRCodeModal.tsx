import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { Dialog, DialogHeader, DialogContent, DialogFooter } from '../ui/dialog'
import { Button } from '../ui/button'
import { Card, CardContent } from '../ui/card'
import { Download, X, Copy, Printer, QrCode } from 'lucide-react'
import toast from 'react-hot-toast'

interface QRCodeModalProps {
  tokenCode: string | null
  onClose: () => void
}

export default function QRCodeModal({ tokenCode, onClose }: QRCodeModalProps) {
  const [qrImage, setQrImage] = useState<string | null>(null)

  const { data: token, isLoading } = useQuery({
    queryKey: ['ticket-qr', tokenCode],
    queryFn: async () => {
      if (!tokenCode || tokenCode === 'new') return null
      const response = await api.get<{ qr_data: string; qr_payload: string }>(`/tickets/${tokenCode}/qr`)
      return response.data
    },
    enabled: !!tokenCode && tokenCode !== 'new',
  })

  useEffect(() => {
    if (token?.qr_data) {
      setQrImage(`data:image/png;base64,${token.qr_data}`)
    } else {
      setQrImage(null)
    }
  }, [token])

  const handleDownload = () => {
    if (!qrImage) return
    const link = document.createElement('a')
    link.href = qrImage
    link.download = `${tokenCode}-qrcode.png`
    link.click()
    toast.success('QR code berhasil diunduh')
  }

  const handleCopy = async () => {
    if (!token?.qr_payload) return
    await navigator.clipboard.writeText(token.qr_payload)
    toast.success('Data QR disalin ke papan klip')
  }

  const handlePrint = () => {
    window.print()
  }

  if (!tokenCode) return null

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader
          icon={<QrCode className="h-5 w-5" strokeWidth={3} />}
          tone="bg-nb-cyan"
          title={`QR: ${tokenCode}`}
          description="Pindai kode QR ini di gerbang untuk validasi masuk/keluar"
        />

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <span className="flex h-20 w-20 animate-nb-pulse items-center justify-center rounded-md border-2 border-ink bg-nb-cyan text-ink shadow-nb-sm">
              <QrCode className="h-9 w-9" />
            </span>
            <p className="nb-label mt-4 text-muted-foreground">Membuat kode QR…</p>
          </div>
        ) : qrImage ? (
          <div className="space-y-5">
            {/* QR Code Display */}
            <div className="flex justify-center">
              {/* Kept on a flat white plate so the code stays machine-scannable */}
              <img
                src={qrImage}
                alt={`Kode QR untuk tiket ${tokenCode}`}
                className="mx-auto h-64 w-64 border-4 border-ink bg-white p-4 shadow-nb-lg"
              />
            </div>

            {/* Ticket Info Card */}
            <Card className="nb-card-hover overflow-hidden bg-muted">
              <CardContent className="space-y-2 p-4 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="nb-label text-muted-foreground">Kode</span>
                  <span className="truncate font-mono font-extrabold">{tokenCode}</span>
                </div>
                <div className="nb-divider" />
                <div className="flex items-center justify-between gap-3">
                  <span className="nb-label text-muted-foreground">Payload</span>
                  <span className="max-w-[220px] truncate font-mono text-xs font-semibold">
                    {token?.qr_payload}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Action Buttons — a 2×2 grid so the four actions read as one
                block instead of a stack of mismatched widths. */}
            <DialogFooter className="grid grid-cols-2 gap-3">
              <Button
                onClick={handleDownload}
                className="gap-2 bg-nb-cyan text-ink shadow-nb hover:shadow-nb-lg"
              >
                <Download className="h-4 w-4" strokeWidth={3} />
                Unduh PNG
              </Button>
              <Button
                onClick={handleCopy}
                className="gap-2 bg-nb-purple text-ink shadow-nb hover:shadow-nb-lg"
              >
                <Copy className="h-4 w-4" strokeWidth={3} />
                Salin Payload
              </Button>
              <Button
                onClick={handlePrint}
                className="gap-2 bg-nb-orange text-ink shadow-nb hover:shadow-nb-lg"
              >
                <Printer className="h-4 w-4" strokeWidth={3} />
                Cetak Tiket
              </Button>
              <Button variant="outline" onClick={onClose} className="gap-2">
                <X className="h-4 w-4" strokeWidth={3} />
                Tutup
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <span className="flex h-20 w-20 items-center justify-center rounded-md border-2 border-ink bg-nb-orange text-ink shadow-nb-sm">
              <QrCode className="h-9 w-9" />
            </span>
            <p className="mt-4 text-lg font-extrabold uppercase tracking-tight">Kode QR tidak tersedia</p>
            <p className="mt-1 max-w-xs text-sm font-semibold text-muted-foreground">
              Tiket ini belum memiliki payload QR. Terbitkan secara manual atau perbarui tiket untuk
              menghasilkan ulang.
            </p>
            <DialogFooter>
              <Button variant="outline" onClick={onClose} className="gap-2">
                <X className="h-4 w-4" strokeWidth={3} />
                Tutup
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}