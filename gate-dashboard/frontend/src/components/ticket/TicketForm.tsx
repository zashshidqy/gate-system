import { useState } from 'react'
import { Dialog, DialogHeader, DialogContent, DialogFooter } from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Select, SelectItem } from '../ui/select'
import { X, Ticket } from 'lucide-react'
import { TicketToken, TicketType } from '../../types'
import { format, addDays } from 'date-fns'

interface TicketFormProps {
  ticket: TicketToken | null
  onClose: () => void
  onSubmit: (data: any) => void
  isLoading: boolean
}

export default function TicketForm({ ticket, onClose, onSubmit, isLoading }: TicketFormProps) {
  const initialMetadata = ticket?.metadata
    ? JSON.stringify(ticket.metadata, null, 2)
    : '{"visitor_name": "John Doe", "vehicle_type": "car"}';

  const [formData, setFormData] = useState({
    type: ticket?.type || 'SINGLE_ENTRY',
    valid_from: ticket?.valid_from ? ticket.valid_from.replace(' ', 'T').substring(0, 16) : format(new Date(), "yyyy-MM-dd'T'HH:mm"),
    valid_until: ticket?.valid_until ? ticket.valid_until.replace(' ', 'T').substring(0, 16) : format(addDays(new Date(), 1), "yyyy-MM-dd'T'HH:mm"),
    max_uses: ticket?.max_uses || 1,
    metadata: initialMetadata,
  })

  const isEdit = !!ticket

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    let metadataObj = {}
    try {
      metadataObj = formData.metadata ? JSON.parse(formData.metadata) : {}
    } catch {
      metadataObj = {}
    }
    onSubmit({ ...formData, metadata: metadataObj })
  }

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader
          icon={<Ticket className="h-5 w-5" strokeWidth={3} />}
          tone="bg-nb-pink"
          title={isEdit ? 'Ubah Tiket' : 'Buat Tiket'}
          description={
            isEdit ? 'Ubah detail token tiket' : 'Terbitkan token tiket baru beserta kode QR'
          }
        />

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="type">Jenis Tiket</Label>
            <Select
              value={formData.type}
              onValueChange={(v) => setFormData((prev) => ({ ...prev, type: v as TicketType }))}
            >
              <SelectItem value="SINGLE_ENTRY">Sekali Masuk</SelectItem>
              <SelectItem value="MULTI_DAY">Multi Hari</SelectItem>
              <SelectItem value="VIP">VIP</SelectItem>
              <SelectItem value="STAFF">Staff</SelectItem>
            </Select>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="valid_from">Mulai Berlaku</Label>
              <Input
                id="valid_from"
                type="datetime-local"
                value={formData.valid_from}
                onChange={(e) => setFormData((prev) => ({ ...prev, valid_from: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="valid_until">Berlaku Sampai</Label>
              <Input
                id="valid_until"
                type="datetime-local"
                value={formData.valid_until}
                onChange={(e) => setFormData((prev) => ({ ...prev, valid_until: e.target.value }))}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="max_uses">Maksimal Pemakaian</Label>
            <Input
              id="max_uses"
              type="number"
              min="1"
              value={formData.max_uses}
              onChange={(e) => setFormData((prev) => ({ ...prev, max_uses: parseInt(e.target.value) || 1 }))}
            />
            <p className="text-xs font-semibold text-muted-foreground">
              Berapa kali tiket ini boleh dipindai sebelum tidak berlaku lagi.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="metadata">Metadata (JSON)</Label>
            <textarea
              id="metadata"
              className="h-28 w-full rounded-md border-2 border-ink bg-card px-3 py-2 font-mono text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-0"
              value={formData.metadata}
              onChange={(e) => setFormData((prev) => ({ ...prev, metadata: e.target.value }))}
              placeholder='{"visitor_name": "John Doe", "vehicle_type": "car"}'
            />
            <p className="text-xs font-semibold text-muted-foreground">
              Disimpan bersama token dan dikembalikan ke pemindai saat validasi.
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} className="gap-2">
              <X className="h-4 w-4" strokeWidth={3} />
              Batal
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="gap-2 bg-nb-pink text-ink shadow-nb hover:shadow-nb-lg"
            >
              {isLoading ? 'Menyimpan...' : isEdit ? 'Perbarui' : 'Buat'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}