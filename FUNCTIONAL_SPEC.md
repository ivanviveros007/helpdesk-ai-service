# Especificación Funcional — Helpdesk AI

> Documento vivo. Se actualiza a medida que se construye el sistema.
> Última actualización: 2026-05-23 (v2 — invitaciones, multi-tenancy completo, super-admin dashboard)

---

## 1. Visión general

Sistema de mesa de ayuda inteligente donde los tickets de soporte son analizados por IA y asignados automáticamente al técnico más adecuado según la naturaleza del problema, la carga de trabajo actual y los skills de cada técnico.

**Repositorios:**
| Repo | Tech | Puerto |
|---|---|---|
| `helpdesk-backend` | NestJS + TypeORM + PostgreSQL | 3001 |
| `helpdesk-ai-service` | FastAPI + LangChain + ChromaDB + Gemini | 8000 |
| `helpdesk-front` | Next.js 16 + TailwindCSS | 3000 |
| `helpdesk-superadmin` | Next.js 16 + TailwindCSS | 3002 |

---

## 2. Roles y permisos

| Rol | Entidad DB | Quién es | Quién lo crea |
|---|---|---|---|
| **user** | `users` | Cliente que crea tickets | Se auto-registra vía invitación |
| **technician** | `tecnicos` | Técnico de soporte | Admin de la empresa |
| **admin** | `tecnicos` (role=admin) | Administrador de la empresa | Super-admin |
| **superadmin** | `super_admins` | Dueño del SaaS | Seed / manual |

### Qué puede hacer cada rol

| Capacidad | user | technician | admin | superadmin |
|---|---|---|---|---|
| Crear tickets | ✅ | — | — | — |
| Ver sus tickets | ✅ | — | — | — |
| Ver tickets asignados | — | ✅ | ✅ | — |
| Resolver tickets | — | ✅ | ✅ | — |
| Ver todos los tickets (con filtros) | — | — | ✅ | — |
| Gestionar técnicos | — | — | ✅ | — |
| Gestionar niveles | — | — | ✅ | — |
| Invitar clientes | — | — | ✅ | — |
| Ver/crear organizaciones | — | — | — | ✅ |
| Ver métricas globales | — | — | — | ✅ |
| Suspender organizaciones | — | — | — | ✅ |

### Acceso por rol (helpdesk-front — puerto 3000)

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
| `/admin/users` | — | — | ✅ |

### Acceso (helpdesk-superadmin — puerto 3002)

| Pantalla | superadmin |
|---|---|
| `/login` | ✅ |
| `/dashboard` | ✅ |
| `/organizations` | ✅ |
| `/organizations/:id` | ✅ |
| `/logs` | ✅ |

---

## 3. Registro y autenticación

### Flujo de invitación (forma recomendada)
1. Admin de empresa va a `/admin/users` → "Invitar" → ingresa email del cliente
2. `POST /admin/invitations` genera un token UUID con 7 días de vigencia
3. El admin comparte el link: `http://localhost:3000/register?invite={token}`
4. El cliente abre el link → `GET /auth/invite/{token}` valida el token y retorna `{ email, org_nombre, org_id }`
5. El formulario muestra el nombre de la empresa y pre-completa el email (solo requiere nombre + contraseña)
6. `POST /auth/register` con `{ nombre, email, password, invite_token }` → asigna `org_id` desde el token y lo marca como usado

### Registro sin invitación (fallback desarrollo)
- `POST /auth/register` sin `invite_token`
- Se asigna automáticamente la organización `slug: demo`
- Solo útil en desarrollo/testing

### Login
- Ruta: `POST /auth/login`
- El backend busca primero en `tecnicos`, luego en `users`, luego en `super_admins`
- Retorna un JWT con: `{ sub, email, role, entity_type, org_id, nombre }`
- El frontend redirige según el rol:
  - `user` → `/client/my-tickets`
  - `technician` → `/technician`
  - `admin` → `/admin/tickets`
  - `superadmin` → `/dashboard` (en helpdesk-superadmin)

### JWT
- Duración: 7 días
- `entity_type`: `'user'` | `'technician'` | `'superadmin'` — distingue entre las tablas de autenticación
- `org_id`: filtra datos por empresa en todas las queries; `null` para superadmin
- `role`: `'user'` | `'technician'` | `'admin'`

### Tokens de invitación
- Entidad `Invitation`: `{ token (UUID), email, org_id, role, used, expires_at }`
- Un token solo puede usarse una vez (`used: true` tras el registro)
- Expiración: 7 días desde la creación
- `GET /auth/invite/:token` — público, valida y retorna info de la org

---

## 4. Multi-tenancy (Organization)

Cada entidad del sistema pertenece a una organización (`org_id`). Los datos de cada empresa son completamente aislados.

**Entidades con `org_id`:** `Ticket`, `Technician`, `Level`, `User`, `Invitation`.

**Cómo se garantiza el aislamiento:**
- Todos los endpoints de `/admin/*` filtran por `req.user.org_id` (extraído del JWT)
- Al crear cualquier entidad desde el admin, se asigna automáticamente el `org_id` del admin logueado
- Un admin no puede ver ni modificar datos de otra organización

### Ciclo de vida de una organización
1. **Super-admin** crea la org desde `helpdesk-superadmin` → define nombre, slug, plan y admin inicial
2. **Admin** crea técnicos, define niveles, invita clientes
3. **Clientes** se registran vía invitación → crean tickets
4. **Super-admin** puede suspender (`estado_activo: false`) o reactivar la org

### Credenciales de acceso (development)
| Rol | Email | Password |
|---|---|---|
| superadmin | superadmin@helpdesk.app | SuperAdmin1234! |
| admin (demo) | admin@demo.com | Admin1234! |
| técnico (demo) | carlos@demo.com | Tech1234! |
| usuario (demo) | usuario1@test.com | User1234! |

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

Los técnicos son creados directamente por el admin de la empresa — no se auto-registran.

**Campos de un técnico:**
- `nombre`, `email`, `password`
- `nivel`: nivel de soporte asignado (FK → Level)
- `skills`: lista de tecnologías/áreas de expertise (ej: `React Native`, `payments`, `Kotlin`)
- `carga_actual`: cantidad de tickets activos asignados (se incrementa al asignar, decrementa al resolver)
- `estado_activo`: si puede recibir tickets
- `org_id`: asignado automáticamente al org_id del admin que lo crea

**Los skills son texto libre.** La IA los compara semánticamente con el contenido del ticket para decidir la asignación.

**UI:** `/admin/technicians` — tabla con CRUD completo, modal de creación/edición con selector de nivel y gestión de skills por tags.

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
| POST | `/auth/login` | — | Login (técnicos, usuarios, superadmin) |
| POST | `/auth/register` | — | Registro de usuarios (público) |
| GET | `/auth/invite/:token` | — | Validar token de invitación |

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
| GET/POST | `/admin/technicians` | JWT (admin) | Gestión de técnicos (filtrado por org) |
| GET/PATCH/DELETE | `/admin/technicians/:id` | JWT (admin) | Técnico individual |
| GET/POST | `/admin/levels` | JWT (admin) | Gestión de niveles (filtrado por org) |
| GET/PATCH/DELETE | `/admin/levels/:id` | JWT (admin) | Nivel individual |
| GET/POST | `/admin/invitations` | JWT (admin) | Gestión de invitaciones a clientes |

### Super-Admin
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/super-admin/auth/login` | — | Login super-admin |
| GET | `/super-admin/organizations` | SuperAdminGuard | Todas las orgs con stats |
| POST | `/super-admin/organizations` | SuperAdminGuard | Crear org + admin inicial |
| GET/PATCH | `/super-admin/organizations/:id` | SuperAdminGuard | Detalle / actualizar org |
| POST | `/super-admin/organizations/:id/admin` | SuperAdminGuard | Crear admin para una org |
| GET | `/super-admin/metrics` | SuperAdminGuard | KPIs globales del sistema |
| GET | `/super-admin/logs` | SuperAdminGuard | Actividad reciente + errores IA |

### Internal (backend → AI service)
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/api/internal/routing-context` | X-Internal-Secret header | Contexto para routing de IA |

---

## 11. Super-Admin Dashboard (helpdesk-superadmin)

Aplicación separada en puerto 3002 para el dueño del SaaS.

### Pantallas
| Ruta | Descripción |
|---|---|
| `/login` | Login con credenciales de superadmin |
| `/dashboard` | KPIs globales: total orgs, tickets hoy/mes, tiempo promedio resolución |
| `/organizations` | Tabla de todas las orgs con stats + formulario para crear nueva org |
| `/organizations/:id` | Métricas detalladas, suspender/activar, crear admin adicional |
| `/logs` | Feed de actividad reciente + alerta de tickets atascados en PENDIENTE_IA |

### Autenticación separada
- Token guardado en `localStorage` con key `sa_token` (separado del `access_token` de helpdesk-front)
- `SuperAdminGuard` verifica `entity_type === 'superadmin'` en el JWT

---

## 12. Configuración de IA por Organización

Cada organización puede tener un perfil de IA configurado por el superadmin.

**Campos en `Organization`:**
- `company_type`: `'tech_saas'` | `'ecommerce'` | `'healthcare'` | `'retail'` | `'it_services'` | `'other'`
- `ai_custom_instructions`: texto libre con instrucciones adicionales para el agente

**Cómo llega al agente:**
1. Al crear un ticket, el backend envía `org_id` al AI service
2. El AI service inyecta `org_id` en un ContextVar antes de invocar el agente
3. La herramienta `get_routing_context` lee el ContextVar y llama al backend con `?org_id=`
4. El backend retorna `org_context: { company_type, ai_custom_instructions }` + niveles y técnicos filtrados por org
5. El agente lee `org_context` del resultado de la herramienta y ajusta su razonamiento

**Configuración desde superadmin:** `/organizations/:id` → sección "Configuración de IA"

**Endpoint:** `PATCH /super-admin/organizations/:id/ai-config`

---

## 13. Pendiente / Próximas funcionalidades

- [x] Notificaciones por email (Resend) al asignar y resolver tickets
- [x] Contexto de IA por organización (company_type + instrucciones custom)
- [ ] Notificaciones por WhatsApp (Twilio) — segunda etapa
- [ ] Billing con Stripe (por plan: trial / starter / pro / enterprise)
- [ ] Dashboard de métricas para admin (tickets por técnico, tiempo de resolución)
- [ ] Re-envío de invitaciones expiradas
- [ ] Gestión de usuarios desde el panel admin (ver lista de clientes registrados)
