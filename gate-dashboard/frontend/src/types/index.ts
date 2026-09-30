export interface User {
  id: string
  username: string
  email: string | null
  full_name: string | null
  role: 'ADMIN' | 'GUARD' | 'STAFF'
  active: boolean
  created_at: string
  last_login: string | null
}

export type UserRole = 'ADMIN' | 'GUARD' | 'STAFF';

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface GateStatus {
  state: string
  pos: number
  front_cm: number
  vehicle: boolean
  lcd1: string
  lcd2: string
  masters: string[]
  exit_cm: number
  rfid_ver: string
  last_uid: string | null
  last_auth: string | null
  count: number
}

export interface UnitStatus {
  unit: 'ENTRY' | 'EXIT'
  status: GateStatus | null
  connected: boolean
  last_update: string | null
}

export interface GateEvent {
  type: string
  unit?: 'ENTRY' | 'EXIT'
  payload: any
  timestamp: string
}

export type TicketType = 'SINGLE_ENTRY' | 'MULTI_DAY' | 'VIP' | 'STAFF'

export interface TicketToken {
  id: string
  code: string
  qr_payload: string
  type: TicketType
  valid_from: string
  valid_until: string
  max_uses: number
  used_count: number
  issued_by: string
  issued_at: string
  revoked: boolean
  metadata: Record<string, any> | null
}

export interface TicketValidationRequest {
  token_code: string
  gate: 'ENTRY' | 'EXIT'
  method: 'QR_SCAN' | 'RFID_LINK' | 'MANUAL' | 'ANPR'
}

export interface TicketValidationResponse {
  allowed: boolean
  reason: string | null
  token: TicketToken | null
  usage_id: string | null
}

export interface TicketUsage {
  id: string
  token_id: string
  gate_id: string
  direction: string
  timestamp: string
  allowed: boolean
  method: string
  note: string | null
}

export interface QRCodeResponse {
  token_code: string
  qr_data: string
  qr_payload: string
}

export interface AuthorizedCard {
  id: string
  uid: string
  label: string | null
  added_by: string
  added_at: string
  active: boolean
  note: string | null
}

export interface Passage {
  id: number
  ts: string
  direction: 'ENTRY' | 'EXIT'
  method: 'RFID' | 'ANPR' | 'MANUAL' | 'QR'
  uid: string | null
  plate: string | null
  allowed: boolean
  image_path: string | null
  note: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PassageFilter {
  direction?: 'ENTRY' | 'EXIT'
  method?: 'RFID' | 'ANPR' | 'MANUAL' | 'QR'
  allowed?: boolean
  date_from?: string
  date_to?: string
  search?: string
  page: number
  page_size: number
}