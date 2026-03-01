# RheXa Backend Monitoring & Observability Setup

## 📊 Monitoring Stack Overview

This guide covers setting up comprehensive monitoring for the RheXa Backend including:
- Application metrics (Prometheus)
- Time-series visualization (Grafana)
- Log aggregation (ELK Stack)
- Distributed tracing (Jaeger)
- Alerting (AlertManager)

---

## 🔍 Prometheus Metrics Integration

### Step 1: Install Prometheus Client

```bash
pip install prometheus-client
```

### Step 2: Add Metrics to FastAPI

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
REQUEST_COUNT = Counter(
    'rhexa_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'rhexa_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'rhexa_active_connections',
    'Number of active connections'
)

# Database metrics
DB_QUERY_DURATION = Histogram(
    'rhexa_db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table']
)

DB_CONNECTIONS = Gauge(
    'rhexa_db_connections',
    'Number of database connections',
    ['state']
)

# LLM metrics
LLM_LATENCY = Histogram(
    'rhexa_llm_latency_seconds',
    'LLM API latency',
    ['model', 'provider']
)

LLM_TOKENS = Counter(
    'rhexa_llm_tokens_total',
    'Total tokens used',
    ['model', 'type']
)

# Vector search metrics
VECTOR_SEARCH_DURATION = Histogram(
    'rhexa_vector_search_duration_seconds',
    'Vector similarity search duration',
    ['k', 'index_size']
)
```

### Step 3: Add Prometheus Middleware

```python
# app/main.py
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from app.core.metrics import REQUEST_COUNT, REQUEST_DURATION

app = FastAPI()

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def add_prometheus_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response
```

---

## 📈 Grafana Dashboard Setup

### Prometheus Data Source

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### Key Dashboards

**1. API Performance Dashboard**
```
- Request Rate: sum(rate(rhexa_requests_total[5m])) by (method)
- Response Time: histogram_quantile(0.95, rhexa_request_duration_seconds)
- Error Rate: sum(rate(rhexa_requests_total{status=~"5.."}[5m]))
- Active Connections: rhexa_active_connections
```

**2. Database Dashboard**
```
- Query Duration: histogram_quantile(0.95, rhexa_db_query_duration_seconds) by (operation)
- Connection Pool: rhexa_db_connections by (state)
- Query Rate: sum(rate(rhexa_db_query_duration_seconds[5m])) by (operation)
- Slow Queries: rhexa_db_query_duration_seconds > 1
```

**3. LLM Performance Dashboard**
```
- API Latency: histogram_quantile(0.95, rhexa_llm_latency_seconds) by (provider)
- Token Usage: sum(rate(rhexa_llm_tokens_total[1h])) by (model, type)
- Cost Estimation: Total tokens * price per token
- Model Performance: Latency trends over time
```

---

## 📝 ELK Stack for Logging

### Install Elasticsearch, Logstash, Kibana

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### Configure Application Logging

```python
# app/core/logging.py
import logging
from pythonjsonlogger import jsonlogger

# JSON structured logging
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)

logger = logging.getLogger("rhexa")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Log levels
DEBUG_LOGGER = logger.getChild("debug")
ERROR_LOGGER = logger.getChild("error")
ACCESS_LOGGER = logger.getChild("access")
```

### Logstash Configuration

```
input {
  tcp {
    port => 5000
    codec => json
  }
}

filter {
  if [type] == "rhexa" {
    date {
      match => [ "timestamp", "ISO8601" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "rhexa-%{+YYYY.MM.dd}"
  }
}
```

---

## 🔔 Alerting with AlertManager

### Alert Rules (Prometheus)

```yaml
# alerts.yml
groups:
  - name: rhexa-alerts
    rules:
      # API Alerts
      - alert: HighErrorRate
        expr: sum(rate(rhexa_requests_total{status=~"5.."}[5m])) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rhexa_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "High API latency"
          description: "P95 latency is {{ $value }}s"
      
      # Database Alerts
      - alert: SlowQueries
        expr: histogram_quantile(0.95, rhexa_db_query_duration_seconds) > 2
        for: 5m
        annotations:
          summary: "Slow database queries"
      
      - alert: ConnectionPoolExhausted
        expr: rhexa_db_connections{state="active"} > 80
        for: 2m
        annotations:
          summary: "Database connection pool nearly exhausted"
      
      # LLM Alerts
      - alert: HighLLMLatency
        expr: histogram_quantile(0.95, rhexa_llm_latency_seconds) > 30
        for: 10m
        annotations:
          summary: "High LLM API latency"
      
      - alert: LLMErrors
        expr: sum(rate(rhexa_llm_errors_total[5m])) > 0.1
        for: 5m
        annotations:
          summary: "LLM API errors"
```

### AlertManager Configuration

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'critical'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    - receiver: 'slack'
      match:
        severity: 'warning'
    
    - receiver: 'pagerduty'
      match:
        severity: 'critical'

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_URL}
        channel: '#alerts'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: ${PAGERDUTY_KEY}
```

---

## 🔍 Distributed Tracing with Jaeger

### Install Jaeger Client

```bash
pip install jaeger-client
```

### Configure Tracing

```python
# app/core/tracing.py
from jaeger_client import Config
from opentracing_instrumentation.client_hooks import install_all_patches

def init_tracing():
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        service_name='rhexa-backend',
        validate=True,
    )
    
    jaeger_tracer = config.initialize_tracer()
    install_all_patches()
    
    return jaeger_tracer

tracer = init_tracing()
```

### Add to FastAPI

```python
from fastapi.openapi.utils import get_openapi
from opentracing_instrumentation.local_span import LocalSpanManager

app = FastAPI()

@app.middleware("http")
async def add_tracing(request, call_next):
    with tracer.start_active_span(
        operation_name=f"{request.method} {request.url.path}"
    ) as scope:
        response = await call_next(request)
        return response
```

---

## 📊 Health Check & Status Page

### Implement Health Checks

```python
# app/api/routes/health.py
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db.session import SessionLocal

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    
    # Database check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Redis check (if configured)
    try:
        # Add Redis health check
        health_status["checks"]["cache"] = "ok"
    except Exception as e:
        health_status["checks"]["cache"] = f"error: {str(e)}"
    
    # External services check
    try:
        # Check OpenAI connectivity
        health_status["checks"]["openai"] = "ok"
    except Exception as e:
        health_status["checks"]["openai"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status
```

---

## 📋 Monitoring Checklist

### Pre-Production
- [ ] Prometheus installed and configured
- [ ] Grafana dashboards created
- [ ] Alert rules defined
- [ ] AlertManager configured
- [ ] Logging aggregation setup
- [ ] Jaeger tracing enabled
- [ ] Health checks implemented

### Post-Deployment
- [ ] Monitor metrics for 24 hours
- [ ] Verify alerts trigger correctly
- [ ] Test failover scenarios
- [ ] Document runbooks for alerts
- [ ] Configure log retention
- [ ] Setup dashboard backups
- [ ] Establish SLOs and SLIs

### Ongoing
- [ ] Review metrics weekly
- [ ] Adjust alert thresholds
- [ ] Update dashboards as needed
- [ ] Clean old logs
- [ ] Performance optimization
- [ ] Capacity planning

---

## 🚀 Docker Compose for Full Stack

See `docker-compose.monitoring.yml` for complete ELK + Prometheus + Grafana stack.

---

## 📚 References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Elastic Stack](https://www.elastic.co/what-is/elk-stack)
- [Jaeger Tracing](https://www.jaegertracing.io/)
- [OpenTelemetry](https://opentelemetry.io/)
