# SYSTEM_MAP

```
                 ┌───────────────┐
                 │    NetBox     │
                 │  (SoT técnico)│
                 └──────┬────────┘
                        │ Webhooks
                        ▼
                  ┌────────────┐
                  │    N8N     │
                  │ Orquestra  │
                  └────┬──┬────┘
           ┌───────────┘  └───────────┐
           ▼                           ▼
    ┌────────────┐             ┌───────────────┐
    │   Zabbix   │             │    Grafana    │
    │ Monitoring │             │ Visualização  │
    └────────────┘             └──────┬────────┘
           │                          │
           ▼                          ▼
    ┌────────────┐             ┌────────────┐
    │ PostgreSQL │             │   Redis    │
    │ Audit/DLQ  │             │ Queue/Cache│
    └────────────┘             └────────────┘

netops_netbox_sync → auditoria NetBox ⇄ dispositivo
Git → templates, dashboards, taxonomia, workflows e docs
```