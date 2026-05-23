# SaaS Roadmap — Helpdesk AI

## Objetivo
Convertir el sistema actual (mono-tenant, local) en un producto SaaS multi-tenant listo para vender a empresas.

---

## 1. Multi-tenancy

**Por qué es lo primero:** afecta toda la arquitectura de DB y queries. Más difícil de agregar después.

- Agregar tabla `Organization` (nombre, subdominio, plan, estado)
- Agregar `org_id` en `Ticket`, `Technician`, `Level`, `User`
- Todas las queries filtran por `org_id` (nunca se mezclan datos entre clientes)
- Subdominio por tenant: `acme.helpdesk.app`, `globo.helpdesk.app`
- ChromaDB: colección separada por tenant o namespace por `org_id`

---

## 2. Self-service onboarding

- Página de registro público: nombre empresa, email, plan elegido
- Email de verificación
- Setup wizard post-registro: crear niveles de soporte, invitar técnicos
- Primer login → redirige al wizard si la cuenta está incompleta

---

## 3. Billing y planes

- Integración con **Stripe**: suscripciones mensuales y anuales
- Planes diferenciados, por ejemplo:
  | Plan | Límites |
  |---|---|
  | Starter | 500 tickets/mes, 3 técnicos |
  | Pro | 5.000 tickets/mes, técnicos ilimitados |
  | Enterprise | Sin límite, SLA, soporte dedicado |
- Portal de facturación (Stripe Customer Portal)
- Webhooks de Stripe para activar, suspender o cancelar cuentas automáticamente
- Bloqueo graceful al superar límites del plan

---

## 4. Infraestructura cloud

Hoy todo corre local. Para producción:

| Componente | Opción recomendada |
|---|---|
| Backend NestJS | Railway / Render / AWS ECS |
| AI Service FastAPI | Railway / Render / AWS ECS |
| PostgreSQL | Supabase / AWS RDS |
| ChromaDB | Pinecone o Weaviate (managed) |
| Frontend Next.js | Vercel |
| Dominio + SSL | Cloudflare |
| Secrets / env vars | Doppler / AWS Secrets Manager |
| CI/CD | GitHub Actions |

---

## 5. Observabilidad y operaciones

- Logs centralizados: Datadog / Logtail / Axiom
- Alertas de errores en runtime: Sentry (backend + frontend)
- Métricas de uso por tenant: tickets procesados, tiempo de respuesta IA, tasa de resolución
- Dashboard interno de superadmin: ver todos los tenants, MRR, churn, uso

---

## 6. Seguridad y compliance

- Rate limiting por tenant (evitar abuso)
- Audit log: registro inmutable de quién hizo qué y cuándo
- Backups automáticos de DB
- GDPR: exportación de datos del cliente, derecho al olvido
- SOC 2 Type II si se apunta a clientes enterprise (proceso largo, ~6-12 meses)

---

## Orden de implementación sugerido

```
1. Multi-tenancy        ← base de todo, hacerlo primero
2. Self-service onboarding
3. Billing (Stripe)
4. Deploy cloud (staging → producción)
5. Observabilidad
6. Seguridad y compliance
```

---

## Estado actual del sistema

| Componente | Tech | Estado |
|---|---|---|
| Backend | NestJS + TypeORM + PostgreSQL | Completo, mono-tenant |
| AI Service | FastAPI + LangChain + ChromaDB + Gemini | Completo, mono-tenant |
| Frontend | Next.js 16 + TailwindCSS | Completo, mono-tenant |
| Multi-tenancy | — | Pendiente |
| Billing | — | Pendiente |
| Cloud deploy | — | Pendiente |
| Observabilidad | — | Pendiente |
