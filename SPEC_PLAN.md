# Spec Plan — Helpdesk AI → CRM de Reclamos Post-venta

> Documento de especificación para implementación con Fable 5.
> Autor: sesión de diseño del producto — 2026-06-11
> Estado: listo para implementación

---

## 1. Visión del producto

### Qué estamos construyendo
Un SaaS de gestión de reclamos post-venta para PYMEs LATAM. El cliente que compró algo y tiene un problema reclama por WhatsApp, email, o widget. La IA clasifica el reclamo y lo deriva al agente correcto. El cliente hace seguimiento sin crear una cuenta.

### Quién lo usa
- **Empresa (tenant):** paga el SaaS. Tiene agentes que resuelven reclamos.
- **Cliente final:** compró algo, tiene un problema. Nunca sabe que existe esta plataforma — solo ve la marca de la empresa.
- **Superadmin:** Iván — gestiona las organizaciones y planes.

### ICP principal
E-commerce DTC en México/Colombia/Chile con 300–3,000 pedidos/mes. 3–10 personas en atención al cliente. Hoy gestiona reclamos por WhatsApp personal + Gmail sin trazabilidad.

### Diferenciadores clave
1. 100% enfocado en post-venta — no soporte genérico
2. WhatsApp como canal bidireccional nativo (no add-on)
3. Cliente final hace seguimiento sin cuenta (magic link por token)
4. IA clasifica por categorías de post-venta (no detección genérica)
5. Pricing flat — no por agente
6. 100% en español, pensado para LATAM

---

## 2. Qué cambia vs el producto actual

| Concepto actual | Concepto nuevo |
|---|---|
| `técnico` / `technician` | `agente` / `agent` |
| `ticket` | `reclamo` / `complaint` |
| `nivel` (jerarquía técnica) | `categoría de reclamo` |
| Cliente necesita invitación + cuenta | Cliente final no necesita nada |
| Un solo punto de entrada (formulario) | Email + WhatsApp + Widget + Form público |
| Sin portal público | Portal por token sin cuenta |
| IA enruta por nivel técnico | IA enruta por categoría de reclamo |
| Estética gradientes / "startup IA" | Estética Notion/Linear — limpia y profesional |

---

## 3. Sistema de diseño — Estética Notion/Linear

### Principios
- **Blanco como base** — fondos blancos o gris muy claro (#FAFAFA). Sin gradientes en fondos.
- **Tipografía limpia** — Inter o Geist, tamaños consistentes, peso semibold para títulos.
- **Espacio generoso** — padding amplio, elementos que respiran.
- **Un solo color de acento** — por defecto `#2F6FED` (azul medio). Customizable por org en el widget.
- **Bordes sutiles** — `border: 1px solid #E5E7EB` (gray-200). Sin sombras pesadas.
- **Iconos simples** — Lucide Icons exclusivamente.
- **Badges de estado** con colores semánticos suaves (no saturados):
  - `PENDIENTE_IA` → gris claro `bg-gray-100 text-gray-600`
  - `ABIERTO` → azul claro `bg-blue-50 text-blue-700`
  - `EN_PROGRESO` → naranja claro `bg-orange-50 text-orange-700`
  - `ESPERANDO_CLIENTE` → púrpura claro `bg-purple-50 text-purple-700`
  - `RESUELTO` → verde claro `bg-green-50 text-green-700`
  - `CANCELADO` → gris `bg-gray-100 text-gray-500`

### Layout del panel de agentes
```
┌─────────────────────────────────────────────────────────────┐
│ Sidebar (240px)  │  Main content area  │  Context panel     │
│                  │                     │  (320px, colapsable)│
│ Logo empresa     │  Lista de reclamos  │  Datos del cliente  │
│ ─────────────── │  o detalle          │  Historial          │
│ Reclamos         │                     │  Pedido vinculado   │
│ Clientes         │                     │  Notas internas     │
│ ─────────────── │                     │                     │
│ Configuración    │                     │                     │
└─────────────────────────────────────────────────────────────┘
```

### Sidebar
- Fondo blanco, border-right `1px solid #E5E7EB`
- Items: ícono Lucide + texto, `hover:bg-gray-50`, activo con `bg-gray-100 text-gray-900 font-medium`
- Logo de la empresa en la parte superior
- Sin colores fuertes en el sidebar

### Tablas / Listas de reclamos
- Header con `text-xs text-gray-500 uppercase tracking-wide`
- Filas con `hover:bg-gray-50`, `border-bottom: 1px solid #F3F4F6`
- Sin borders laterales en las celdas
- Columnas: #ID, Asunto, Cliente, Canal (ícono), Estado (badge), Prioridad, Agente, Fecha

### Formularios
- Labels `text-sm font-medium text-gray-700`
- Inputs `border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500`
- Sin bordes de colores en estado normal

---

## 4. Cambios de arquitectura — Base de datos

### 4.1 Tabla `tickets` — modificaciones

Agregar columnas a la tabla existente:

```sql
-- Canal de entrada
ALTER TABLE tickets ADD COLUMN channel VARCHAR(20) DEFAULT 'form';
-- Valores: 'email' | 'whatsapp' | 'widget' | 'form' | 'instagram'

-- Datos del cliente final (no requiere cuenta)
ALTER TABLE tickets ADD COLUMN customer_email VARCHAR(255);
ALTER TABLE tickets ADD COLUMN customer_name VARCHAR(255);
ALTER TABLE tickets ADD COLUMN customer_phone VARCHAR(50);

-- Token para seguimiento sin cuenta
ALTER TABLE tickets ADD COLUMN tracking_token VARCHAR(64) UNIQUE;
ALTER TABLE tickets ADD COLUMN tracking_token_expires_at TIMESTAMP;

-- Categoría de reclamo (reemplaza el uso de nivel para clasificación)
ALTER TABLE tickets ADD COLUMN complaint_category_id UUID REFERENCES complaint_categories(id);

-- Flujo de resolución actual
ALTER TABLE tickets ADD COLUMN resolution_type VARCHAR(50);
-- Valores: 'replacement' | 'refund' | 'repair' | 'credit' | 'information' | null

-- Número de pedido externo (referencia al e-commerce)
ALTER TABLE tickets ADD COLUMN order_reference VARCHAR(100);

-- CSAT post-resolución
ALTER TABLE tickets ADD COLUMN csat_score INTEGER; -- 1-5
ALTER TABLE tickets ADD COLUMN csat_comment TEXT;
ALTER TABLE tickets ADD COLUMN csat_sent_at TIMESTAMP;

-- Incidente masivo
ALTER TABLE tickets ADD COLUMN incident_id UUID REFERENCES incidents(id);
```

### 4.2 Nueva tabla `complaint_categories`

Categorías de reclamo configuradas por cada organización.

```sql
CREATE TABLE complaint_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id VARCHAR NOT NULL,
  name VARCHAR(100) NOT NULL,         -- "Problema de entrega"
  slug VARCHAR(50) NOT NULL,          -- "delivery_issue"
  description TEXT,
  icon VARCHAR(50),                   -- nombre del ícono Lucide
  color VARCHAR(7),                   -- hex color para el badge
  default_priority INTEGER DEFAULT 2, -- 1=alta, 2=media, 3=baja
  sla_first_response_hours INTEGER,   -- horas para primera respuesta
  sla_resolution_hours INTEGER,       -- horas para resolución
  resolution_flow JSONB,              -- pasos del flujo guiado
  is_active BOOLEAN DEFAULT true,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Categorías default que se crean al registrar una nueva org:
-- { name: "Problema de entrega", slug: "delivery", icon: "Truck" }
-- { name: "Producto defectuoso", slug: "defective", icon: "PackageX" }
-- { name: "Cobro incorrecto", slug: "billing", icon: "CreditCard" }
-- { name: "Solicitud de devolución", slug: "return", icon: "RotateCcw" }
-- { name: "Garantía", slug: "warranty", icon: "Shield" }
-- { name: "Otro", slug: "other", icon: "HelpCircle" }
```

### 4.3 Nueva tabla `macros`

Respuestas rápidas con variables y acciones compuestas.

```sql
CREATE TABLE macros (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id VARCHAR NOT NULL,
  name VARCHAR(100) NOT NULL,         -- "Confirmar recepción de devolución"
  body TEXT NOT NULL,                 -- Texto con variables: {{customer_name}}, {{order_reference}}, {{ticket_id}}
  actions JSONB,                      -- [{ "type": "set_status", "value": "ESPERANDO_CLIENTE" }, { "type": "set_category", "value": "return" }]
  is_shared BOOLEAN DEFAULT true,     -- false = solo visible para el agente que la creó
  created_by VARCHAR,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Variables disponibles en el body:
-- {{customer_name}}     → nombre del cliente final
-- {{ticket_id}}         → ID corto del reclamo (#4521)
-- {{order_reference}}   → número de pedido
-- {{org_name}}          → nombre de la empresa
-- {{agent_name}}        → nombre del agente que aplica la macro
-- {{tracking_url}}      → link de seguimiento del cliente
```

### 4.4 Nueva tabla `incidents` (Incidente masivo)

Un problema que afecta a múltiples clientes simultáneamente.

```sql
CREATE TABLE incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id VARCHAR NOT NULL,
  title VARCHAR(255) NOT NULL,        -- "Demora en envíos — proveedor Andreani"
  description TEXT,
  status VARCHAR(20) DEFAULT 'open',  -- 'open' | 'investigating' | 'resolved'
  affected_count INTEGER DEFAULT 0,   -- calculado dinámicamente
  update_message TEXT,                -- mensaje de actualización masiva
  resolved_at TIMESTAMP,
  created_by VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Relación: ticket tiene incident_id (FK)
-- Cuando se resuelve un incidente, se notifica a todos los clientes vinculados
```

### 4.5 Nueva tabla `org_integrations`

Configuración de canales y webhooks por organización.

```sql
CREATE TABLE org_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id VARCHAR NOT NULL,
  provider VARCHAR(30) NOT NULL,
  -- Valores: 'email_inbound' | 'whatsapp' | 'slack' | 'teams' | 'widget' | 'instagram'
  config JSONB NOT NULL,
  -- email_inbound:  { "inbound_address": "acme@inbound.tuproducto.com" }
  -- whatsapp:       { "phone_number": "+521234567890", "twilio_sid": "...", "twilio_token": "..." }
  -- slack:          { "access_token": "xoxb-...", "channel_id": "C123", "channel_name": "#soporte" }
  -- teams:          { "webhook_url": "https://outlook.office.com/webhook/..." }
  -- widget:         { "primary_color": "#2F6FED", "position": "right", "welcome_message": "..." }
  is_active BOOLEAN DEFAULT true,
  events TEXT[] DEFAULT '{complaint.created,complaint.resolved}',
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.6 Nueva tabla `sla_policies`

```sql
CREATE TABLE sla_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id VARCHAR NOT NULL,
  name VARCHAR(100) NOT NULL,
  priority INTEGER,                   -- 1=alta, 2=media, 3=baja, null=todos
  category_id UUID REFERENCES complaint_categories(id),
  first_response_hours INTEGER NOT NULL,
  resolution_hours INTEGER NOT NULL,
  business_hours_only BOOLEAN DEFAULT false,
  notify_agent_at_percent INTEGER DEFAULT 80, -- notificar al 80% del SLA
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.7 Nueva tabla `customer_notes`

Notas internas sobre el cliente final (visibles solo para el equipo).

```sql
CREATE TABLE customer_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id VARCHAR NOT NULL,
  customer_email VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  created_by VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 5. Specs de features por fase

---

### FASE 0 — Redesign visual y renaming (sin features nuevas)

**Objetivo:** hacer el producto visualmente más serio y profesional antes de mostrar a clientes.

#### 0.1 Renaming en toda la app

| Antes | Después | Archivos afectados |
|---|---|---|
| "técnico" / "technician" | "agente" / "agent" | helpdesk-front, helpdesk-backend |
| "ticket" | "reclamo" | helpdesk-front, helpdesk-backend, helpdesk-superadmin |
| "Mesa de Ayuda" / "Helpdesk" | "Reclamos" / "Gestión Post-venta" | Labels en UI |
| "niveles" (en contexto de routing) | "categorías" | helpdesk-front |

**Importante:** renaming es de UI/labels solamente. Los nombres de tablas en DB, endpoints y variables de código pueden quedar como están para no generar deuda de migración innecesaria.

#### 0.2 Redesign visual — helpdesk-front

Aplicar el sistema de diseño Notion/Linear definido en la sección 3 a todas las pantallas existentes:

- **Layout general:** Sidebar blanco con border-right sutil. Sin gradientes en backgrounds.
- **Sidebar:** Rediseñar con ícono + texto, hover states suaves, active state con `bg-gray-100`.
- **Tablas:** Header en `text-xs uppercase text-gray-500`. Filas con hover `bg-gray-50`. Sin sombras.
- **Badges de estado:** Reemplazar por badges suaves (ver paleta en sección 3).
- **Cards:** Bordes `1px solid #E5E7EB`, sin sombras fuertes, `rounded-lg`.
- **Botones primarios:** `bg-blue-600 hover:bg-blue-700 text-white`, sin gradientes.
- **Formularios:** Inputs con border-gray-300, focus ring azul.
- **Pantallas a redesignar:** login, dashboard técnico/agente, admin/tickets, admin/technicians, admin/levels, admin/users, admin/metrics, /tickets/:id (detalle), client/new-ticket, client/my-tickets.

#### 0.3 Redesign visual — helpdesk-superadmin

Mismos principios. Pantallas: dashboard, organizations, organizations/:id, logs.

---

### FASE 1 — Core post-venta (entrada pública + tracking sin cuenta)

#### 1.1 Portal público de reclamos

**Qué es:** URL pública por organización donde el cliente final puede crear un reclamo sin cuenta.

**URL:** `app.tuproducto.com/p/[org-slug]`

**Pantalla:**
```
Logo + nombre de la empresa (configurados en org settings)
────────────────────────────────────────
Título: "¿Tuviste un problema con tu compra?"
Subtítulo: "Creá tu reclamo y te contactamos en menos de [SLA horas]"

Formulario:
  - Nombre completo *
  - Email *
  - Teléfono (opcional)
  - Número de pedido (opcional, label customizable por la org)
  - Categoría del reclamo * (dropdown con las categorías activas de la org)
  - Descripción * (textarea)
  - Adjuntos (hasta 5 archivos, 10MB c/u)

Botón: "Enviar reclamo"

Footer: "Atendido con [nombre del producto]" (removible en plan Pro)
```

**Flujo tras submit:**
1. Se crea el ticket en DB con `channel = 'form'`, `tracking_token` generado (UUID v4, expira en 90 días)
2. IA clasifica y asigna (flujo existente, adaptado a categorías)
3. Se envía email al cliente con:
   - Confirmación de recepción
   - Número de reclamo (#ID corto)
   - Link de seguimiento: `app.tuproducto.com/p/[org-slug]/seguimiento?token=[tracking_token]`
4. Si la org tiene Slack/Teams configurado: notificación al canal
5. Reclamo aparece en el panel del agente

**API endpoint nuevo:**
```
POST /public/[org-slug]/complaints
Body: { customer_name, customer_email, customer_phone?, order_reference?, category_id, description, attachments? }
Response: { complaint_id, tracking_token, short_id }
```

**Configuración en org settings:**
- `public_portal_enabled: boolean`
- `public_portal_slug: string` (único, generado del nombre de la org)
- `portal_logo_url: string`
- `portal_primary_color: string`
- `portal_welcome_message: string`
- `portal_order_label: string` — label del campo número de pedido (ej: "Número de pedido", "Número de factura", "Código de reserva")

#### 1.2 Página de seguimiento por token (sin cuenta)

**URL:** `app.tuproducto.com/p/[org-slug]/seguimiento?token=[token]`

**Pantalla:**
```
Logo empresa
────────────────────────────────────────
Reclamo #4521
Categoría: Producto defectuoso
Estado: 🟡 En progreso

Timeline:
  ✅ 10/06 14:32 — Reclamo recibido
  ✅ 10/06 14:33 — Asignado a Ana García
  🔵 11/06 09:15 — Ana: "Hola Juan, necesitamos una foto del defecto"
  🔵 11/06 10:02 — [foto adjunta por cliente]

Responder:
  [textarea] [adjuntar archivo] [Enviar]
────────────────────────────────────────
```

**Reglas:**
- Token inválido o expirado: mensaje de error con email de contacto de la org
- El cliente puede agregar comentarios y adjuntos desde esta página
- Cada respuesta del cliente genera notificación al agente (email + WebSocket)
- No se muestra información de otros reclamos (el token solo da acceso a ESE reclamo)

**API endpoints nuevos:**
```
GET  /public/complaints/track?token=[token]
POST /public/complaints/track/[token]/reply
Body: { body, attachments? }
```

#### 1.3 Email-to-ticket (inbound email parsing)

**Qué es:** Cada organización recibe una dirección de email dedicada. Los emails que llegan a esa dirección se convierten automáticamente en reclamos.

**Dirección formato:** `[org-slug]@inbound.[dominio-saas].com`

**Flujo:**
1. Configurar Resend (o SendGrid) con inbound email webhook
2. Email llega → Resend parsea → POST webhook a `POST /inbound/email`
3. Backend extrae: remitente (→ customer_email), asunto (→ ticket.asunto), cuerpo (→ descripcion_raw), adjuntos (→ R2)
4. Crea ticket con `channel = 'email'`, `tracking_token` generado
5. IA clasifica (flujo existente)
6. Responde al cliente con email de confirmación + link de seguimiento

**Comportamiento de respuestas:** Si el cliente responde al email de confirmación, el reply se agrega como comentario al reclamo (parsear `In-Reply-To` o header de ticket ID en el asunto).

**Configuración visible en org settings:**
```
Email de soporte: [org-slug]@inbound.tuproducto.com   [Copiar]
Podés configurar un reenvío desde tu email actual hacia esta dirección.
```

**Módulo backend nuevo:** `src/inbound/` con `InboundEmailController`, `InboundEmailService`

#### 1.4 Context Panel del agente

**Qué es:** Panel lateral derecho en la vista de detalle de reclamo que muestra información del cliente y su historial.

**Componente:** `ComplaintContextPanel` (nuevo, en `/tickets/:id`)

**Contenido:**
```
Cliente
─────────────────────────────
Nombre: Juan Pérez
Email: juan@gmail.com
Teléfono: +5491155551234
Canal: WhatsApp

Historial con esta empresa
─────────────────────────────
3 reclamos anteriores
  • #4210 - Entrega demorada - RESUELTO (hace 2 meses)
  • #3891 - Cobro incorrecto - RESUELTO (hace 4 meses)
  • #3102 - Producto defectuoso - CANCELADO (hace 7 meses)

Reclamo actual
─────────────────────────────
Categoría: Producto defectuoso
Canal: Email
Número de pedido: #ORD-8821
Creado: hace 2 horas
SLA primera respuesta: ⚠️ vence en 1.5 horas

Notas internas del equipo
─────────────────────────────
[textarea para agregar notas]
[notas existentes del cliente]
```

**API endpoint nuevo:**
```
GET /tickets/:id/customer-context
Response: { customer_history: Ticket[], customer_notes: Note[], sla_status: SLAStatus }
```

#### 1.5 Categorías de reclamo — Admin

**Pantalla nueva:** `/admin/categories`

El admin puede ver, crear, editar y desactivar las categorías de reclamo de su organización.

**Campos editables por categoría:**
- Nombre, descripción, ícono (selector de Lucide icons), color del badge
- Prioridad por defecto
- SLA primera respuesta (horas), SLA resolución (horas)
- Flujo de resolución guiado (pasos opcionales, JSONB)
- Activa / inactiva

**Al crear una nueva organización:** poblar automáticamente con 6 categorías default (ver tabla en 4.2).

---

### FASE 2 — Herramientas de resolución

#### 2.1 Macros / Respuestas rápidas

**Pantalla nueva:** `/admin/macros`

El admin gestiona las macros del equipo. Cada macro tiene:
- Nombre (interno, solo lo ve el equipo)
- Texto de respuesta con soporte de variables `{{variable}}`
- Acciones opcionales: cambiar estado, asignar categoría
- Visibilidad: compartida (todo el equipo) o personal

**Uso en el panel del agente:**
- Botón "Respuestas rápidas" en el área de texto de respuesta
- Dropdown con macros disponibles (filtradas por texto)
- Al seleccionar: llena el textarea con el texto, aplica las acciones definidas
- El agente puede editar el texto antes de enviar

**Variables disponibles:**
```
{{customer_name}}   → nombre del cliente
{{ticket_id}}       → ID del reclamo (ej: #4521)
{{order_reference}} → número de pedido
{{org_name}}        → nombre de la empresa
{{agent_name}}      → nombre del agente
{{tracking_url}}    → link de seguimiento
{{category_name}}   → nombre de la categoría
```

#### 2.2 Incidente masivo

**Pantalla nueva:** `/admin/incidents`

Permite crear un incidente que agrupa múltiples reclamos del mismo problema.

**Flujo:**
1. Admin detecta patrón (o sistema lo sugiere — ver 4.1) y crea un incidente
2. Puede vincular reclamos existentes al incidente manualmente o por búsqueda de categoría/fecha
3. Los reclamos vinculados muestran banner: "Este reclamo es parte del incidente: [título]"
4. Cuando el admin escribe una actualización y la publica: se notifica a TODOS los clientes vinculados simultáneamente (email + WhatsApp si aplica)
5. Al resolver el incidente: todos los reclamos vinculados se marcan como RESUELTO con la nota de resolución

**Detección automática (IA):** Si 5+ reclamos de la misma categoría se crean en menos de 24hs, el sistema alerta al admin: "⚠️ Detectamos 8 reclamos de 'Problema de entrega' en las últimas 6 horas. ¿Querés crear un incidente?"

**API endpoints nuevos:**
```
GET    /incidents
POST   /incidents
PATCH  /incidents/:id
POST   /incidents/:id/link-tickets   Body: { ticket_ids: string[] }
POST   /incidents/:id/broadcast      Body: { message: string }
POST   /incidents/:id/resolve        Body: { resolution_message: string }
```

#### 2.3 SLAs

**Configuración en org settings:**
- Políticas de SLA por prioridad y/o categoría
- Horas de primera respuesta y resolución
- Si aplica solo en horario laboral

**Indicadores en el panel:**
- Columna "SLA" en la tabla de reclamos: verde (OK) / amarillo (>80%) / rojo (vencido)
- En detalle del reclamo: barra de progreso con tiempo restante
- Badge de "SLA VENCIDO" en rojo sobre el reclamo

**Alertas:**
- Email al agente asignado cuando el SLA supera el 80%
- Email al admin cuando el SLA vence
- WebSocket push para actualizar el indicador en tiempo real

**Lógica de cálculo:**
```
SLA primera respuesta: desde created_at hasta el primer comentario del agente
SLA resolución: desde created_at hasta estado = RESUELTO
Si business_hours_only: excluir horario fuera de las horas configuradas por la org
```

#### 2.4 CSAT post-resolución

**Flujo:**
1. Reclamo pasa a estado RESUELTO
2. Sistema espera 2 horas (configurable)
3. Envía email/WhatsApp al cliente con:
   ```
   ¿Quedaste conforme con la resolución de tu reclamo?
   
   ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐  ⭐⭐⭐  ⭐⭐  ⭐
   
   [campo: comentario opcional]
   ```
4. Cliente hace clic en una estrella (link con rating en la URL): `POST /public/csat?token=[token]&score=[1-5]`
5. Score se guarda en el ticket (`csat_score`, `csat_comment`)

**Dashboard de admin:**
- CSAT promedio del período
- CSAT por agente
- CSAT por categoría
- Distribución de scores (gráfico de barras)
- Comentarios negativos (score 1-2) destacados para review

---

### FASE 3 — Canales adicionales

#### 3.1 Widget embebible

**Qué es:** Un snippet de JavaScript que la empresa pega en su sitio. Aparece como botón flotante. Al hacer clic, abre un panel de chat/formulario branded con la empresa.

**Instalación:**
```html
<script>
  window.ComplaintsWidget = { orgSlug: 'acme-store' };
</script>
<script src="https://app.tuproducto.com/widget.js" async></script>
```

**Comportamiento del widget:**
1. Botón flotante (bottom-right por defecto, posición configurable)
2. Al abrir: muestra saludo + opciones de categoría como botones
3. Cliente selecciona categoría → formulario contextual (campos según la categoría)
4. Submit → crea reclamo con `channel = 'widget'`
5. Respuesta: "Reclamo #4521 creado. Te notificamos a [email] con el seguimiento."

**Personalización desde org settings:**
- Color primario
- Posición (derecha/izquierda)
- Texto del botón launcher
- Mensaje de bienvenida
- Logo

**Archivos a crear:**
- `helpdesk-front/public/widget.js` — script vanilla JS (sin React, carga un iframe)
- `helpdesk-front/src/app/widget/[org-slug]/page.tsx` — contenido del iframe

#### 3.2 WhatsApp (Twilio)

**Arquitectura:**
1. La empresa conecta su número de WhatsApp Business a Twilio
2. Configura el webhook de Twilio apuntando a: `POST /inbound/whatsapp`
3. Mensaje llega → backend lo recibe → busca si ya existe reclamo abierto del mismo número → si sí, agrega como comentario; si no, crea reclamo nuevo con `channel = 'whatsapp'`
4. Agente responde desde el panel → backend llama Twilio API → mensaje llega al WhatsApp del cliente en el hilo original

**Variables de env a agregar al backend:**
```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
```

**Módulo backend nuevo:** `src/inbound/whatsapp.controller.ts`

**UX en el panel del agente:**
- Reclamos de WhatsApp muestran ícono de WhatsApp verde en la columna Canal
- El área de respuesta se ve igual que los otros canales — el agente no necesita saber nada de Twilio

---

### FASE 4 — Integraciones y notificaciones

#### 4.1 Webhooks salientes genéricos

**Tabla `org_integrations`** ya incluye soporte para webhooks.

**Panel de configuración:** `/admin/integrations`

Para cada integración disponible, el admin ve una card con:
- Logo e instrucciones de configuración
- Formulario para ingresar credenciales/URL
- Toggle activo/inactivo
- Selector de eventos a notificar

**Slack:**
- El admin hace clic en "Conectar Slack"
- OAuth flow → bot token → selector de canal
- Eventos: `complaint.created`, `complaint.assigned`, `complaint.resolved`, `sla.breached`, `incident.created`
- Formato del mensaje en Slack: bloque con nombre del cliente, categoría, link al reclamo

**Teams:**
- El admin pega una URL de Incoming Webhook de Teams
- Mismo set de eventos
- Formato: Adaptive Card

**Zapier:**
- Exponer webhooks trigger en la documentación
- Cada org tiene una URL de webhook incoming para conectar desde Zapier

---

### FASE 5 — Landing page rewrite

#### 5.1 Nuevo copy y posicionamiento

**Archivo principal:** `helpdesk-landing/components/sections/Hero.tsx` y demás secciones.

**Cambios de copy:**

**Hero:**
```
Headline: "Gestioná los reclamos de tus clientes sin perder ninguno"
Subheadline: "WhatsApp, email y web en un solo lugar. La IA clasifica y 
              deriva automáticamente. El cliente sigue su caso sin crear cuenta."
CTA: "Empezar gratis — 14 días sin tarjeta"
Secondary CTA: "Ver demo"
```

**Sección Problema:**
```
Sin tu herramienta:
❌ Reclamo por WhatsApp → nadie lo ve → cliente furioso
❌ Email en Gmail → se pierde entre otros → sin respuesta  
❌ No sabés cuántos reclamos tenés abiertos

Con tu herramienta:
✅ Todo llega a un lugar — WhatsApp, email, formulario
✅ IA clasifica y asigna al agente correcto en segundos
✅ El cliente sigue el estado con un solo clic, sin registrarse
```

**Sección Cómo funciona (4 pasos):**
1. El cliente reclama — por WhatsApp, email o tu sitio web
2. La IA clasifica el reclamo y lo asigna al responsable
3. El agente responde desde un panel unificado
4. El cliente recibe la respuesta en el mismo canal donde escribió

**Sección Para quién:**
- Tiendas online con más de 100 pedidos al mes
- Empresas de servicios con contratos de mantenimiento
- Cualquier negocio que hoy atiende reclamos por WhatsApp y Gmail

**Sección Features (6 tarjetas):**
1. WhatsApp nativo — no un add-on, el canal principal
2. Seguimiento sin cuenta — el cliente ve su estado con un link
3. IA especializada — clasifica por tipo de reclamo post-venta
4. Incidente masivo — un problema de 30 clientes, una sola actualización
5. SLAs automáticos — alertas antes de que venza el tiempo de respuesta
6. Widget en tu sitio — se instala en 2 minutos

**Testimonial placeholder:**
> "Antes perdíamos reclamos en WhatsApp. Ahora sabemos exactamente cuántos 
> hay abiertos, quién los está atendiendo y cuánto tardan en resolverse."
> — CTO, Nebroo

**Pricing section (3 planes):**
```
Starter    $49/mes    Hasta 5 agentes, 3 canales, IA incluida
Pro        $99/mes    Hasta 15 agentes, todos los canales, SLAs, CSAT
Business   $199/mes   Agentes ilimitados, dominio propio, integraciones, soporte prioritario
```

**CTA final:**
```
"Empezar gratis" — 14 días, sin tarjeta, configuración en 5 minutos
```

**Idioma:** Español únicamente en la versión principal. El i18n EN se puede mantener como secondary.

---

## 6. Fases de implementación — orden y prioridad

```
FASE 0 — Redesign + Renaming          (1 semana)
  └── Sin tocar backend. Solo UI/copy/labels.

FASE 1 — Core post-venta              (2-3 semanas)
  └── Portal público → tracking por token → email-to-ticket → context panel → categorías

FASE 2 — Herramientas de resolución   (2 semanas)
  └── Macros → Incidente masivo → SLAs → CSAT

FASE 3 — Canales                      (2 semanas)
  └── Widget JS → WhatsApp Twilio

FASE 4 — Integraciones                (1-2 semanas)
  └── Slack → Teams → Webhooks genéricos

FASE 5 — Landing                      (3-5 días)
  └── Rewrite copy + nuevo posicionamiento
```

---

## 7. Repositorios y puertos de referencia

| Repo | Tech | Puerto |
|---|---|---|
| `helpdesk-backend` | NestJS + TypeORM + PostgreSQL | 3001 |
| `helpdesk-ai-service` | FastAPI + LangChain + ChromaDB + Gemini/Groq | 8000 |
| `helpdesk-front` | Next.js 15 App Router + TailwindCSS | 3000 |
| `helpdesk-superadmin` | Next.js 15 App Router + TailwindCSS | 3002 |
| `helpdesk-landing` | Next.js + i18n (EN/ES) | 3003 |

**Paths locales:** `/Users/bambam/Documents/coding/helpdesk-ai/[repo]`

---

## 8. Credenciales y servicios activos

- **DB:** PostgreSQL local — `postgresql://bambam@localhost:5432/helpdesk_db`
- **Email:** Resend — `noreply@helpdesk-ai.cloud` — dominio verificado
- **Storage:** Cloudflare R2 — bucket `helpdesk-attachments`
- **IA:** Groq `llama-3.3-70b-versatile` (LLM) + Gemini `gemini-embedding-001` (embeddings)
- **Dominio:** `helpdesk-ai.cloud` configurado en Vercel + Hostinger DNS

---

## 9. Notas para el implementador (Fable 5)

1. **Empezar siempre por la Fase 0** — el redesign visual define el tono de todo lo que viene. Usar el sistema de diseño de la sección 3 en todos los componentes nuevos.

2. **Los endpoints existentes no se rompen** — las fases 1-4 son aditivas. El flujo actual de tickets sigue funcionando; se extiende con nuevas columnas y nuevos endpoints.

3. **El tracking_token** se genera en el backend al crear el ticket. Usar `crypto.randomBytes(32).toString('hex')` para 64 chars hex. Siempre verificar expiración en los endpoints públicos.

4. **Los endpoints públicos** (`/public/...`) no llevan JWT. Usar el `tracking_token` como auth para las operaciones del cliente final.

5. **Para las migraciones de DB** usar TypeORM migrations (`npm run migration:generate` en helpdesk-backend). No usar `synchronize: true` en producción.

6. **El widget** (`widget.js`) debe ser vanilla JS sin dependencias externas para minimizar el impacto en el sitio del cliente. El contenido se carga en un iframe apuntando a una ruta del frontend.

7. **CSAT emails** se envían desde un cron job similar al de inactividad ya existente en `TicketsCron`.

8. **Categorías default** deben crearse automáticamente en el seed y en el hook de creación de organización (`POST /organizations`).
