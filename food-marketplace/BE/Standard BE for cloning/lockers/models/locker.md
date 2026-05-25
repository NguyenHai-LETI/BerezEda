Shop (1) ──► LockerLocation (N) ──► LockerUnit (N) ──► LockerReservation (N)
     │              │                     │                      │
     │              │                     │                      ▼
     │              │                     │                   User (1)
     │              │                     │
     │              │                     ▼ (also relates to)
     │              │               LockerReservation (N)
     │              │
     └──────────────┴─────────────► LockerReservation (N)

available → [reserve] → reserved → [deposit] → occupied → [collect] → cleaning → [complete]→available
↓              ↓              ↓              ↓              ↓
Firebase       Firebase       Firebase       Firebase       Firebase