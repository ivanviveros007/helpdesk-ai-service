# Especificación Funcional — Helpdesk AI

> Documento vivo. Se actualiza a medida que se construye el sistema.
> Última actualización: 2026-05-23

---

## 1. Visión general

Sistema de mesa de ayuda inteligente donde los tickets de soporte son analizados por IA y asignados automáticamente al técnico más adecuado según la naturaleza del problema, la carga de trabajo actual y los skills de cada técnico.

**Repositorios:**
| Repo | Tech | Puerto |
|---|---|---|
| `helpdesk-backend` | NestJS + TypeORM + PostgreSQL | 3001 |
| `helpdesk-ai-service` | FastAPI + LangChain + ChromaDB + Gemini | 8000 |
| `helpdesk-front` | Next.js 16 + TailwindCSS | 3000 |

---

## 2. Roles y permisos

| Rol | Quién es | Qué puede hacer |
|---|---|---|
| **user** | Cliente que usa el sistema de soporte | Crear tickets, ver sus propios tickets |
| **technician** | Técnico de soporte | Ver tickets asignados, cambiar estado, resolver tickets |
| **admin** | Administrador de la empresa | Todo lo anterior + gestionar técnicos y niveles, ver todos los tickets con filtros |

### Acceso por rol (frontend)

| Pantalla | user | technician | admin |
|---|---|---|---|
| `/register` | ✅ | ✅ | ✅ |
| `/login` | ✅ | ✅ | ✅ |
| `/client/new-ticket` | ✅ | — | — |
| `/client/my-tickets` | ✅ | — | — |
| `/technician` | — | ✅ | — |
| `/admin/tickets` | — | — | ✅ |
| `/admin/technicians` | — | — | ✅ |
| `/admin/levels` | — | — | ✅ |

---

## 3. Registro y autenticación

### Registro de usuarios (self-service)
- Ruta: `POST /auth/register`
- Cualquier persona puede crear una cuenta con nombre, email y contraseña
- Al registrarse, se le asigna automáticamente la organización por defecto (`slug: demo`)
- Tras el registro, se inicia sesión automáticamente y se redirige a `/client/my-tickets`

### Login
- Ruta: `POST /auth/login`
- El backend busca primero en la tabla de técnicos y luego en la de usuarios
- Retorna un JWT con: `{ sub, email, role, entity_type, org_id, nombre }`
- El frontend redirige según el rol:
  - `user` → `/client/my-tickets`
  - `technician` → `/technician`
  - `admin` → `/admin/tickets`

### JWT
- Duración: 7 días
- Incluye `entity_type` ('user' | 'technician') para distinguir entre las dos tablas de autenticación
- Incluye `org_id` para filtrar datos por empresa en todas las queries

---

## 4. Multi-tenancy (Organization)

Cada entidad del sistema pertenece a una organización (`org_id`). Esto permite que en el futuro múltiples empresas usen el mismo sistema de forma aislada.

**Estado actual:** una sola organización (`Empresa Demo`, slug: `demo`). Estructura preparada para múltiples tenants.

**Entidades con `org_id`:** `Ticket`, `Technician`, `Level`, `User`.

---

## 5. Gestión de niveles (Admin)

Los niveles definen la complejidad de los tickets que puede atender cada técnico.

**Campos de un nivel:**
- `numero_nivel`: número entero (1, 2, 3…)
- `nombre`: nombre descriptivo (ej: "Soporte Básico")
- `descripcion_responsabilidades`: texto libre que explica qué tipo de problemas cubre
- `tags`: palabras clave que la IA usa para clasificar tickets (ej: `accounts`, `payments`, `security`)
- `max_complexity_score`: puntaje máximo de complejidad (1-10) que puede manejar este nivel

**Ejemplo de configuración:**
| Nivel | Nombre | Tags | Max complejidad |
|---|---|---|---|
| 1 | Soporte Básico | `accounts`, `password`, `onboarding` | 3 |
| 2 | Soporte Técnico | `web`, `mobile`, `payments`, `bugs` | 7 |
| 3 | Ingeniería Avanzada | `security`, `infrastructure`, `performance` | 10 |

---

## 6. Gestión de técnicos (Admin)

**Campos de un técnico:**
- `nombre`, `email`, `password`
- `nivel`: nivel de soporte asignado (FK → Level)
- `skills`: lista de tecnologías/áreas de expertise (ej: `React Native`, `payments`, `Kotlin`)
- `carga_actual`: cantidad de tickets activos asignados (se incrementa al asignar, decrementa al resolver)
- `estado_activo`: si puede recibir tickets

**Los skills son texto libre.** La IA los compara semánticamente con el contenido del ticket para decidir la asignación.

---

## 7. Flujo completo de un ticket

### 7.1 Creación
1. Usuario logueado va a `/client/new-ticket` y completa:
   - **Asunto** (5-200 caracteres)
   - **Descripción** (10-5000 caracteres)
2. `POST /tickets` (requiere JWT)
3. El ticket se crea en estado `PENDIENTE_IA` con el `created_by_user_id` y `org_id` del usuario
4. El backend retorna `{ ticket_id, status }` inmediatamente (sin esperar a la IA)
5. El ticket aparece en la lista del usuario con badge gris "Pendiente IA"

### 7.2 Análisis por IA (asíncrono, ~5-10 segundos)
El AI Service recibe el ticket y ejecuta el siguiente pipeline:

```
1. Limpieza del texto
   └── Normalización unicode, eliminación de caracteres de control, truncado a 4000 chars

2. Embedding
   └── Genera vector con Gemini text-embedding-004

3. RAG (Retrieval Augmented Generation)
   └── Busca en ChromaDB tickets históricos similares (top 3, umbral coseno 0.75)
   └── Agrega contexto relevante al prompt del agente

4. Contexto de routing
   └── Llama a GET /api/internal/routing-context (protegido con X-Internal-Secret)
   └── Obtiene técnicos disponibles con sus skills, nivel y carga actual

5. Agente LangGraph (ReAct)
   └── Razona sobre el ticket con el contexto RAG + técnicos disponibles
   └── Decide: categoría, prioridad (1-10), nivel sugerido, técnico más adecuado
   └── Retorna JSON estructurado con la decisión

6. Almacenamiento en ChromaDB
   └── Guarda el ticket procesado como histórico para futuros RAG
```

### 7.3 Asignación
1. El backend recibe la decisión de la IA
2. Actualiza el ticket: estado → `ASIGNADO`, asigna técnico, guarda categoría/prioridad/razonamiento
3. Incrementa `carga_actual` del técnico asignado
4. Emite eventos WebSocket:
   - `ticket:assigned_to_you` → al room `tech:{technicianId}` (notifica al técnico)
   - `ticket:status_changed` → al room `user:{userId}` (notifica al usuario creador)

### 7.4 Notificación en tiempo real
- El usuario ve el badge cambiar de gris (`PENDIENTE_IA`) a azul (`ASIGNADO`) sin recargar la página
- Aparece el nombre del técnico asignado
- El técnico ve el nuevo ticket en su dashboard en tiempo real

### 7.5 Resolución
- El técnico (o admin) hace click en "Resolver" en el ticket
- `PATCH /tickets/:id/resolve` → estado → `RESUELTO`
- Se decrementa `carga_actual` del técnico
- El usuario ve el badge cambiar a verde (`RESUELTO`) en tiempo real

---

## 8. WebSocket

**Librería:** Socket.IO  
**Namespace:** `/tickets`  
**URL:** `NEXT_PUBLIC_WS_URL/tickets` (default: `http://localhost:3001/tickets`)

### Rooms
| Room | Quién se une | Para qué |
|---|---|---|
| `tech:{technicianId}` | Técnico al conectarse (query param: `technicianId`) | Recibir tickets asignados |
| `user:{userId}` | Usuario al conectarse (query param: `userId`) | Recibir cambios de estado de sus tickets |

### Eventos emitidos por el servidor
| Evento | Destinatario | Cuándo |
|---|---|---|
| `ticket:assigned_to_you` | `tech:{id}` | La IA asignó un ticket a este técnico |
| `ticket:status_changed` | `user:{id}` | El ticket del usuario cambió de estado |

### Payload de los eventos
```typescript
{
  ticketId: string
  status: "PENDIENTE_IA" | "ASIGNADO" | "RESUELTO"
  category: string | null
  priority: number | null          // 1-10
  level: number | null             // nivel asignado
  assignedTechnicianId: string | null
  assignedTechnicianName: string | null
  reasoning: string | null         // explicación del agente IA
  createdByUserId: string | null
  updatedAt: string                // ISO 8601
}
```

---

## 9. Estados de un ticket

```
PENDIENTE_IA  ──(IA procesa)──>  ASIGNADO  ──(técnico/admin resuelve)──>  RESUELTO
    (gris)                        (azul)                                    (verde)
```

---

## 10. API endpoints principales

### Auth
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/login` | — | Login (técnicos y usuarios) |
| POST | `/auth/register` | — | Registro de usuarios (público) |

### Tickets
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/tickets` | JWT (any) | Crear ticket |
| GET | `/tickets/my-tickets` | JWT (user) | Tickets del usuario logueado |
| GET | `/tickets/admin` | JWT (admin) | Todos los tickets con filtros |
| GET | `/tickets` | JWT (any) | Todos los tickets de la org |
| GET | `/tickets/:id` | JWT (any) | Detalle de un ticket |
| GET | `/tickets/technician/:id` | JWT (any) | Tickets de un técnico |
| PATCH | `/tickets/:id/resolve` | JWT (any) | Marcar como resuelto |

### Admin
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET/POST | `/admin/technicians` | JWT (admin) | Gestión de técnicos |
| GET/PATCH/DELETE | `/admin/technicians/:id` | JWT (admin) | Técnico individual |
| GET/POST | `/admin/levels` | JWT (admin) | Gestión de niveles |
| GET/POST | `/admin/users` | JWT (admin) | Gestión de usuarios |

### Internal (backend → AI service)
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/api/internal/routing-context` | X-Internal-Secret header | Contexto para routing de IA |

---

## 11. Pendiente / Próximas funcionalidades

- [ ] Notificaciones por email (Resend) al asignar y resolver tickets
- [ ] Notificaciones por WhatsApp (Twilio) — segunda etapa
- [ ] Self-service onboarding de nuevas organizaciones
- [ ] Billing con Stripe
- [ ] Dashboard de métricas para admin (tickets por técnico, tiempo de resolución, etc.)
- [ ] Portal de administración SaaS (gestión de todos los tenants)
