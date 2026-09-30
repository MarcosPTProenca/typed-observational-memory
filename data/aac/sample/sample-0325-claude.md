# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HTTP DB Java Tracer is a zero-intrusion Java agent that captures actual ResultSet data from JDBC queries **and HTTP request/response data from Spring Boot applications** without modifying application source code. It uses ByteBuddy for runtime bytecode instrumentation and exports telemetry via OpenTelemetry Protocol (OTLP) in JSON format.

**Core Principle**: The agent intercepts JDBC calls and HTTP requests transparently, capturing query results incrementally as the application reads them and correlating them with HTTP traces, then exports structured telemetry to an OpenTelemetry Collector.

**New in 2025**: HTTP Request/Response tracing with distributed trace correlation (W3C Trace Context).

## Essential Commands

### Build Commands
```bash
# Build agent (produces agent/build/libs/http-db-java-tracer.jar)
./gradlew :agent:shadowJar
make build-agent  # equivalent

# Build all modules
./gradlew build

# Clean everything
./gradlew clean
```

### Test Commands
```bash
# Full integration test with MySQL + OpenTelemetry Collector
make test-with-mysql

# Test HTTP request/response tracing (Spring Boot + 20 integration tests)
make test-with-http

# Test with JPA/Hibernate
make test-with-jpa

# Test with MyBatis
make test-with-mybatis

# Deploy full web application stack (MySQL + Agent + Collector)
make deploy-web-app
```

### OpenTelemetry Verification
```bash
# View captured data in collector logs
make show-collector-logs

# Follow logs in real-time
make show-collector-live

# Verify service.name attribution
make check-service-name

# View captured database queries
make check-db-queries

# View HTTP request/response traces
make check-http-traces
```

### Docker Environment
```bash
# Start MySQL + OpenTelemetry Collector
make docker-up

# Stop all services
make docker-down
```

## Architecture Overview

### Data Flow

**HTTP + Database Trace Flow (Combined)**:

```
HTTP Request → Spring DispatcherServlet
    ↓ [HttpRequestInterceptorAdvice intercepts doDispatch]
    → Extract or Generate TraceContext (W3C traceparent)
    → Attach TraceContext + HttpSpanData to request via VirtualField
    → Start HTTP span (trace.id, span.id, parent.span.id)
         ↓
    Spring Controller → Service Layer → JDBC Call
         ↓ [DatabaseInterceptorAdvice intercepts Statement.executeQuery]
    → Retrieve TraceContext from VirtualField
    → SQL executes normally
         ↓
    → ResultSet created
         ↓ [VirtualField attaches ResultSetMonitor with trace context]
    → Application reads: rs.next(), rs.getString(), etc.
         ↓ [ResultSetInterceptorAdvice captures data incrementally]
    → ResultSetMonitor accumulates row data + trace context
         ↓
    → ResultDataCollector buffers DB spans (per-request ThreadLocal)
         ↓
    HTTP Response Sent
         ↓ [HttpRequestInterceptorAdvice.onExit]
    → Complete HttpSpanData (status, headers, body, duration)
    → Collect all DB spans for this request
    → Create combined TraceExportBatch (1 HTTP span + N DB spans)
         ↓
    ┌───────────┴────────────┐
    ↓                        ↓
OtlpHttpExporter      (JSON file export removed)
    ↓
OtlpJsonHttpExporter (custom JSON format)
    ↓
OpenTelemetry Collector
    ↓
Trace Visualization (Jaeger, Zipkin, Grafana)
```

**Key Points**:
- HTTP span is created first and becomes the parent of all DB spans in that request
- All spans share the same `trace.id` for correlation
- DB spans have `parent.span.id` = HTTP span's `span.id` (flat hierarchy)
- Export happens when HTTP response completes (atomic visibility)
- W3C Trace Context propagated via `traceparent` header

### Key Components by Concern

**Instrumentation Layer** (ByteBuddy transformers)
- `Agent.java` - Entry point (premain/agentmain)
- `ServiceMonitorAgent.java` - Installs ByteBuddy transformations (DB + HTTP)
- `DatabaseInterceptorAdvice.java` - Intercepts Statement.execute*() methods
- `ResultSetInterceptorAdvice.java` - Intercepts ResultSet.getXXX() methods
- **`HttpRequestInterceptorAdvice.java`** - **[NEW]** Intercepts Spring DispatcherServlet.doDispatch
- **`TraceContextInjectorAdvice.java`** - **[NEW]** Injects traceparent into outgoing requests
- `StatementInterceptor.java` - Additional statement interception logic

**Capture Layer** (data collection)
- `ResultSetMonitor.java` - Per-ResultSet instance tracking via VirtualField
- `VirtualField.java` - ByteBuddy utility to attach metadata to objects
- `ResultDataCollector.java` - Aggregates HTTP + DB spans per request (ThreadLocal)
- `SqlAliasParser.java` - Resolves JPA/Hibernate column aliases to real names
- **`HttpSpanData.java`** - **[NEW]** HTTP request/response data model
- **`TraceContext.java`** - **[NEW]** W3C Trace Context (trace.id, span.id, parent.span.id)

**Export Layer** (telemetry)
- `OtlpHttpExporter.java` - Main coordinator for OTLP export
- `OtlpJsonHttpExporter.java` - Custom JSON-format OTLP exporter (not Protobuf)
- `OtelLogRecordBuilder.java` - Converts DatabaseQueryEvent to LogRecordData (with trace context)
- **`OtelHttpLogBuilder.java`** - **[NEW]** Converts HttpSpanData to LogRecordData
- **`TraceExportBatch.java`** - **[NEW]** Combined HTTP + DB span export container
- `ResourceCache.java` - Caches OpenTelemetry Resource attributes

**Configuration**
- `AgentConfig.java` - Singleton configuration from system properties/env vars (now includes HTTP config)

### Module Structure

```
db-monitor/
├── agent/              # Core Java agent (shadowJar produces distributable)
├── test-app/           # Integration test harnesses (JDBC, JPA, MyBatis)
├── web-app/            # Spring Boot demo application
├── docker/             # Compose stacks for MySQL, Oracle, OTel Collector
│   ├── docker-compose.yml
│   └── otel-collector-config.yaml
└── scripts/            # Verification and ops helpers
```

## Critical Implementation Patterns

### 1. VirtualField Pattern for Stateful Tracking

ByteBuddy cannot modify JDBC class fields, so we use VirtualField to attach metadata:

```java
// When ResultSet is created (DatabaseInterceptorAdvice.java)
ResultSetMonitor monitor = new ResultSetMonitor(sql, resultSet);
VirtualField.set(resultSet, "monitor", monitor);

// When data is read (ResultSetInterceptorAdvice.java)
ResultSetMonitor monitor = VirtualField.get(resultSet, "monitor");
monitor.onGetString(columnIndex, value);
```

**Why this matters**: All ResultSet tracking relies on this pattern. Without VirtualField, there's no way to maintain per-ResultSet state.

### 2. Incremental Capture (Not Bulk)

Data is captured **as the application reads it**, not in one bulk operation:

- `rs.next()` → start new row
- `rs.getString(1)` → capture column 1 value
- `rs.getInt(2)` → capture column 2 value
- ResultSet closes → finalize and export

**Why**: This approach captures exactly what the application reads, with minimal memory overhead. Large result sets won't consume excessive memory if the application only reads a few rows.

### 3. OTLP JSON Format (Not Protobuf)

The agent uses a **custom JSON-format OTLP exporter** (`OtlpJsonHttpExporter.java`):

**Rationale**:
- Human-readable (debuggable with tcpdump, browser dev tools)
- No Protobuf compilation step needed
- Easier integration with non-Protobuf systems

**Verification**: `sudo make verify-json` uses tcpdump to confirm JSON payloads.

### 4. Resource Attribution

OpenTelemetry Resource (service.name, service.version, host.name) **must** be passed from `OtlpHttpExporter` to `OtelLogRecordBuilder`. Using `Resource.getDefault()` results in `unknown_service:java`.

**Correct flow**:
```java
// OtlpHttpExporter.java
Resource resource = ResourceCache.getResource(config);
OtelLogRecordBuilder.build(event, resource);  // Pass resource explicitly
```

### 5. ByteBuddy Advice Restrictions

All interceptor advice methods **must be static** and **should not throw exceptions** that break the application:

```java
<REDACTED_USER>.OnMethodExit
public static void onExit(<REDACTED_USER>.Return ResultSet resultSet) {
    try {
        // Your logic here
    } catch (Throwable t) {
        // Suppress to avoid breaking application
        logger.error("Interception failed", t);
    }
}
```

### 6. HTTP Tracing with VirtualField Pattern

HTTP request metadata is attached to Spring's `HttpServletRequest` using the same VirtualField pattern:

```java
// HttpRequestInterceptorAdvice.java - On request start
TraceContext traceContext = TraceContext.fromTraceparent(traceparentHeader);
HttpSpanData httpSpan = new HttpSpanData(...);
VirtualField.set(request, "traceContext", traceContext);
VirtualField.set(request, "httpSpan", httpSpan);

// DatabaseInterceptorAdvice.java - During query execution
TraceContext context = VirtualField.get(currentRequest, "traceContext");
databaseEvent.setTraceId(context.getTraceId());
databaseEvent.setParentSpanId(context.getSpanId());  // HTTP span ID

// HttpRequestInterceptorAdvice.java - On response complete
HttpSpanData httpSpan = VirtualField.get(request, "httpSpan");
httpSpan.complete(statusCode, responseHeaders, responseBody);
exportTraces(httpSpan);  // Export HTTP + all associated DB spans
```

**Why this matters**:
- Enables trace correlation without request attribute pollution
- Maintains zero-intrusion guarantee (no servlet filters required)
- Works with any servlet container (Tomcat, Jetty, Undertow)

### 7. W3C Trace Context Propagation

The agent implements W3C Trace Context specification for distributed tracing:

**Incoming Request**:
```http
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-d75597dee50b0cac-01
```

**Extraction**:
```java
TraceContext context = TraceContext.fromTraceparent(traceparentHeader);
// Creates new span with same trace ID, but new span ID
```

**Outgoing Request** (future enhancement):
```java
String traceparent = context.toTraceparent();
httpClient.addHeader("traceparent", traceparent);
```

**Format**: `version-trace_id-parent_id-flags`
- `version`: Always `00` (current W3C spec)
- `trace_id`: 128-bit (32 hex chars)
- `parent_id`: 64-bit (16 hex chars) - becomes this span's parent
- `flags`: 01 = sampled, 00 = not sampled

### 8. Flat Hierarchy for Performance

The agent uses a **flat span hierarchy** (not nested):

```
HTTP Span (trace.id=abc, span.id=123, parent.span.id=null)
  ├─ DB Query 1 (trace.id=abc, span.id=456, parent.span.id=123)
  ├─ DB Query 2 (trace.id=abc, span.id=789, parent.span.id=123)
  └─ DB Query 3 (trace.id=abc, span.id=101, parent.span.id=123)
```

**Why flat instead of nested?**:
- Simpler implementation (no span stack required)
- Clearer query independence (queries don't call each other)
- Lower memory overhead (no context propagation between queries)
- Easier to reason about (HTTP → DB relationship is explicit)

**Trade-off**: Cannot represent nested service calls or query chains

## Configuration System

The agent reads configuration from **system properties** (with `-D` prefix) or **environment variables** (with `MONITOR_` prefix):

**Common settings**:
```bash
-Dmonitor.enabled=true
-Dmonitor.capture.maxRows=1000
-Dmonitor.otlp.enabled=true
-Dmonitor.otlp.endpoint=http://localhost:9024/v1/logs
-Dmonitor.otlp.service.name=my-service

# HTTP Tracing (new)
-Dmonitor.http.enabled=true
-Dmonitor.http.maxBodySize=10240
-Dmonitor.http.samplingRate=1.0
```

**Environment variable equivalent**:
```bash
MONITOR_ENABLED=true
MONITOR_CAPTURE_MAXROWS=1000

# HTTP Tracing
MONITOR_HTTP_ENABLED=true
MONITOR_HTTP_MAXBODYSIZE=10240
```

All configuration is centralized in `AgentConfig.java` with sensible defaults.

## HTTP Body Capture (Servlet 3.0)

The agent captures HTTP request and response bodies for POST, PUT, and PATCH requests using transparent Servlet 3.0 stream instrumentation. This feature enables debugging API issues by capturing actual request/response payloads without code changes.

### Feature Overview

**What it captures**:
- HTTP request bodies (JSON, XML, form data, plain text)
- HTTP response bodies (JSON, XML, plain text)
- Metadata: content type, size, truncation status, charset

**What it skips**:
- Binary content (images, PDFs, videos, audio)
- Large payloads beyond configured size limit
- Non-whitelisted content types

**Zero-intrusion guarantee**:
- No servlet filters or request wrappers
- No application code modifications required
- Instrumentation uses VirtualField pattern (no memory leaks)
- Silent failure mode (agent never breaks application)

### Configuration

HTTP body capture is configured via system properties or environment variables:

```bash
# Enable/disable body capture (default: true)
-Dmonitor.http.body.capture.enabled=true
MONITOR_HTTP_BODY_CAPTURE_ENABLED=true

# Max request body size in bytes (default: 10240 = 10KB)
-Dmonitor.http.body.max.request.size=10240
MONITOR_HTTP_BODY_MAX_REQUEST_SIZE=10240

# Max response body size in bytes (default: 10240 = 10KB)
-Dmonitor.http.body.max.response.size=10240
MONITOR_HTTP_BODY_MAX_RESPONSE_SIZE=10240

# Content types to capture (comma-separated whitelist)
-Dmonitor.http.body.content.types=application/json,application/xml,text/xml,text/plain,application/x-www-form-urlencoded,application/graphql
MONITOR_HTTP_BODY_CONTENT_TYPES=application/json,application/xml,text/xml,text/plain,application/x-www-form-urlencoded,application/graphql
```

### Supported Content Types

**Captured (whitelist)**:
- `application/json` - JSON APIs
- `application/xml`, `text/xml` - XML APIs
- `application/x-www-form-urlencoded` - HTML form submissions
- `text/plain` - Plain text data
- `application/graphql` - GraphQL queries

**Skipped (blacklist)**:
- `image/*` - Images (PNG, JPEG, GIF, etc.)
- `video/*` - Video files
- `audio/*` - Audio files
- `application/pdf` - PDF documents
- `application/octet-stream` - Binary data
- `multipart/form-data` - File uploads
- `application/zip`, `application/gzip` - Archives

**Behavior for skipped content**:
- Attribute `http.request.body` set to `"[binary content not captured]"`
- No stream instrumentation applied (zero overhead)

### Size Limits and Truncation

Bodies exceeding configured size limits are **truncated** to prevent memory exhaustion:

**Truncation behavior**:
1. Agent captures first N bytes (e.g., 10KB)
2. Appends marker: `"...[truncated]"`
3. Sets metadata attributes:
   - `http.request.body.truncated` = `true`
   - `http.request.body.size` = original size (e.g., 50000)
4. Application still receives **full body** (zero intrusion)

**Example truncated body**:
```json
{
  "data": "ABCDEFGHIJ..."
}...[truncated]
```

**Verification in collector logs**:
```
Attributes:
     -> http.request.body: Str({...}...[truncated])
     -> http.request.body.truncated: Bool(true)
     -> http.request.body.size: Int(51200)
```

### Async Servlet Support

The agent fully supports Servlet 3.0 async processing using `AsyncListener`:

**Supported patterns**:
- `DeferredResult` (Spring MVC)
- `AsyncContext.start()` (raw Servlet 3.0)
- `<REDACTED_USER>` methods returning `CompletableFuture`

**How it works**:
1. Request body captured **before** async processing starts
2. Response body captured **after** `AsyncContext.complete()`
3. Uses `AtomicBoolean.compareAndSet()` for thread-safe capture
4. Handles `onComplete()`, `onError()`, `onTimeout()` callbacks

**Error handling**:
- If async processing throws exception → response body still captured
- If async times out → timeout response captured
- Span exports regardless of async outcome (no data loss)

**Example**:
```java
<REDACTED_USER>("/async")
public DeferredResult<Map<String, Object>> asyncEndpoint(<REDACTED_USER> Map<String, String> request) {
    DeferredResult<Map<String, Object>> result = new DeferredResult<>(5000L);

    CompletableFuture.supplyAsync(() -> {
        // Heavy processing...
        return response;
    }).thenAccept(result::setResult);

    return result;
}
// Agent captures request body before async starts
// Agent captures response body when DeferredResult completes
```

### Implementation Architecture

**Stream instrumentation** (NoWrapping pattern from Hypertrace):
- `ServletRequestInstrumentation` - Intercepts `HttpServletRequest.getInputStream()`
- `ServletInputStreamInstrumentation` - Intercepts `ServletInputStream.read*()`
- `ServletResponseInstrumentation` - Intercepts `HttpServletResponse.getOutputStream()`
- `ServletOutputStreamInstrumentation` - Intercepts `ServletOutputStream.write*()`

**Buffer classes**:
- `BodyCaptureBuffer` - Size-limited accumulator (uses `BoundedByteArrayOutputStream`)
- `BoundedByteArrayOutputStream` - Enforces max capacity, silent overflow
- `ContentTypeUtils` - Whitelist/blacklist logic
- `CharsetResolver` - Extract charset from Content-Type header

**Export attributes**:
```java
// Body capture attributes
http.request.body: String (truncated at 10KB by default)
http.response.body: String (truncated at 10KB by default)

// Metadata attributes
http.request.body.truncated: Boolean
http.response.body.truncated: Boolean
http.request.body.size: Long (original size in bytes)
http.response.body.size: Long (original size in bytes)
http.request.content_length: Long
http.response.content_length: Long
```

### Troubleshooting

**Problem: Bodies not captured**

Check configuration:
```bash
# Verify body capture is enabled
-Dmonitor.http.body.capture.enabled=true

# Verify content type is whitelisted
-Dmonitor.http.body.content.types=application/json,...
```

Check collector logs for error markers:
```bash
make show-collector-logs | grep "http.request.body"
```

**Problem: Bodies truncated too aggressively**

Increase size limits:
```bash
-Dmonitor.http.body.max.request.size=51200   # 50KB
-Dmonitor.http.body.max.response.size=51200  # 50KB
```

Verify in collector logs:
```
http.request.body.size: Int(51200)
http.request.body.truncated: Bool(false)
```

**Problem: Binary content captured (memory issues)**

Ensure content type blacklist is not bypassed:
```bash
# Check request Content-Type header
curl -X POST http://localhost:8080/api/upload \
  -H "Content-Type: image/png" \
  -d <REDACTED_USER>.png

# Should see in logs:
http.request.body: Str([binary content not captured])
```

**Problem: Async responses incomplete**

Check async timeout configuration:
```java
// Ensure AsyncContext timeout is long enough
DeferredResult<T> result = new DeferredResult<>(30000L); // 30s timeout
```

Verify `AsyncListener` registered:
```bash
# Check agent logs for:
"Registered AsyncListener for async request processing"
```

**Problem: Memory leak with high traffic**

Monitor VirtualField cleanup:
```bash
# Agent automatically cleans up VirtualFields after response completion
# Check for finalizeCapturedBodies() calls in logs
```

If memory grows continuously:
```bash
# Reduce capture size limits
-Dmonitor.http.body.max.request.size=5120   # 5KB
-Dmonitor.http.body.max.response.size=5120  # 5KB

# Or disable body capture temporarily
-Dmonitor.http.body.capture.enabled=false
```

### Performance Characteristics

**Overhead measurements** (T053 benchmark test):
- Average latency: <100ms (1000 requests with 500-byte JSON bodies)
- P95 latency: <150ms
- P99 latency: <200ms
- Memory overhead: ~10KB per concurrent request (bounded by max body size)

**Zero-failure test** (T054 robustness test):
- 10,000 requests with random edge cases
- Edge cases: tiny bodies, 15KB bodies, Unicode, special chars, nested JSON, arrays
- Result: 0 application exceptions caused by agent

**Best practices**:
1. Keep body size limits reasonable (10KB default is safe for most APIs)
2. Use content type whitelist to skip unnecessary captures
3. Monitor memory usage under sustained load
4. Disable body capture for high-throughput endpoints if needed

### Testing HTTP Body Capture

**Run integration tests**:
```bash
# Full test suite (20+ tests covering all user stories)
./gradlew :test-app:test --tests "*BodyCapture*" --tests "*ContentType*" --tests "*AsyncStreaming*" --tests "*PerformanceRobustness*"

# Individual test suites
./gradlew :test-app:test --tests "JsonBodyCaptureTest"        # User Story 1: JSON capture
./gradlew :test-app:test --tests "BodySizeLimitTest"          # User Story 2: Size limits
./gradlew :test-app:test --tests "ContentTypeTest"            # User Story 3: Multiple content types
./gradlew :test-app:test --tests "AsyncStreamingTest"         # User Story 4: Async & chunked
./gradlew :test-app:test --tests "PerformanceRobustnessTest"  # Performance & zero-failure
```

**Verify in OpenTelemetry Collector**:
```bash
# Check captured bodies
make show-collector-logs | grep -A 5 "http.request.body"
make show-collector-logs | grep -A 5 "http.response.body"

# Check truncation metadata
make show-collector-logs | grep "http.request.body.truncated"
```

### Related Files

**Agent implementation**:
- `agent/src/main/java/ai/servicewall/monitor/agent/instrumentation/http/stream/` - Stream instrumentation
- `agent/src/main/java/ai/servicewall/monitor/agent/model/BodyCaptureBuffer.java` - Buffer implementation
- `agent/src/main/java/ai/servicewall/monitor/agent/util/ContentTypeUtils.java` - Content-Type validation
- `agent/src/main/java/ai/servicewall/monitor/agent/export/otel/OtelHttpLogBuilder.java` - Export with body attributes

**Test harness**:
- `test-app/src/main/java/com/servicewall/testapp/http/TestUserController.java` - Test endpoints
- `test-app/src/main/java/com/servicewall/testapp/http/AsyncTestController.java` - Async test endpoints
- `test-app/src/test/java/com/servicewall/testapp/http/` - Integration tests

**Specifications**:
- `specs/006-servlet30-body-capture/spec.md` - Feature specification
- `specs/006-servlet30-body-capture/plan.md` - Implementation plan
- `specs/006-servlet30-body-capture/tasks.md` - Task breakdown (55 tasks)

## OpenTelemetry Semantic Conventions

The agent follows [OpenTelemetry Database Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/database/) and [HTTP Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/http/):

**Resource attributes** (shared across all spans):
- `service.name` - Service identifier (default: `http-db-java-tracer`)
- `service.version` - Agent version
- `host.name` - Application hostname
- `host.ip` - Application IP address (auto-detected)

**Database span attributes** (on each query):
- `db.system` - Database type (mysql, oracle, postgresql)
- `db.statement` - SQL query text
- `db.operation` - Operation type (SELECT, INSERT, UPDATE, DELETE)
- `db.rows.count` - Number of rows returned
- `db.result.data` - Actual result data (JSON string)
- `db.result.columns` - Column metadata (JSON string)
- `db.duration.ms` - Query execution time
- **`trace.id`** - **[NEW]** W3C trace ID (128-bit, 32 hex chars)
- **`span.id`** - **[NEW]** Span ID (64-bit, 16 hex chars)
- **`parent.span.id`** - **[NEW]** Parent span ID (HTTP request span)

**HTTP span attributes** (on each HTTP request/response):
- `http.method` - HTTP method (GET, POST, PUT, DELETE)
- `http.url` - Full request URL
- `http.target` - Request path + query string
- `http.status_code` - Response status code
- `http.scheme` - URL scheme (http, https)
- `http.host` - Host header value
- `http.client_ip` - Client IP address
- `http.duration_ms` - Request duration in milliseconds
- `http.request.headers` - Request headers (JSON, sensitive headers redacted)
- `http.response.headers` - Response headers (JSON)
- `http.request.body` - Request body (truncated at maxBodySize)
- `http.response.body` - Response body (truncated at maxBodySize)
- `trace.id` - W3C trace ID (shared with DB spans)
- `span.id` - HTTP span ID
- `parent.span.id` - Parent span ID (from incoming traceparent, or null for root)

## Development Workflows

### Adding New Database Support

1. **Identify JDBC driver classes** to intercept (usually `com.vendor.jdbc.*`)
2. **Update ServiceMonitorAgent.java** to add new type matchers
3. **Test with new database** using test-app module
4. **Verify column metadata extraction** works for that driver

### Modifying Data Capture Logic

1. **Edit ResultSetMonitor.java** for capture behavior
2. **Edit ResultSetInterceptorAdvice.java** for method interception
3. **Test with large result sets** (>1000 rows) to ensure memory limits work
4. **Verify incremental capture** still functions correctly

### Changing OTLP Export Format

1. **Edit OtelLogRecordBuilder.java** for attribute mapping
2. **Maintain semantic conventions** (see above)
3. **Test with OpenTelemetry Collector** running
4. **Verify service.name appears correctly** in collector logs

## Testing Strategy

### Test Types

The project includes **integration tests only** (no unit tests). All tests in `test-app` and `web-app` modules require external services.

**Integration Test Characteristics**:
- Test the complete agent + instrumentation + export pipeline end-to-end
- Require Docker services (MySQL, OpenTelemetry Collector) to be running
- Start embedded web servers (Tomcat) for HTTP tests
- Make real HTTP requests and database queries
- Verify results by checking OpenTelemetry Collector logs
- Execution time: ~2-3 minutes per test suite

**Required Services** (must be running before tests):
```bash
# Start MySQL + OpenTelemetry Collector
make docker-up

# Verify services are healthy
docker ps | grep -E 'mysql|otel-collector'
docker logs db-monitor-otel-collector --tail 10
```

**Test Modules**:

1. **test-app** - Integration test harness for agent validation
   - `SimpleMySQLTest.java` - Basic JDBC interception
   - `JpaTest.java` - JPA/Hibernate query capture
   - `MyBatisTest.java` - MyBatis SQL mapping tests
   - `test-app/src/test/java/com/servicewall/testapp/http/` - HTTP tracing tests (20+ tests)

2. **web-app** - Demo Spring Boot application (manual testing)
   - No automated tests (used for deployment verification)
   - Manual testing via web UI at `http://localhost:8080`

### Running Tests

**Standard workflow**:

1. **Build agent**: `make build-agent`
2. **Run integration test**: `make test-with-mysql` (or `-jpa`, `-mybatis`, `-http`)
3. **Check collector logs**: `make show-collector-logs`
4. **Verify queries captured**: `make check-db-queries`
5. **Verify service name**: `make check-service-name`

**HTTP Tracing Tests** (requires collector):
```bash
# Run all HTTP body capture tests (20+ tests)
./gradlew :test-app:test --tests "*BodyCapture*" --tests "*ContentType*" --tests "*AsyncStreaming*"

# View captured HTTP traces
make check-http-traces

# View request/response bodies
make show-collector-logs | grep -A 5 "http.request.body"
```

**Test Dependencies**:
- Docker services MUST be running (tests will fail otherwise)
- OpenTelemetry Collector must be reachable at `localhost:9024`
- MySQL must be reachable at `localhost:3306`
- Tests use `<REDACTED_USER>` to restart collector (clean state)

**Test Verification Approach**:
```java
// 1. Send HTTP request or execute SQL query
HttpResponse<String> response = httpClient.send(request, ...);

// 2. Wait for async OTLP export
Thread.sleep(3000);  // 3s for sync, 8s for async tests

// 3. Verify via collector logs
String collectorLogs = getCollectorLogs();  // docker logs command
assertTrue(collectorLogs.contains("http.request.body"));
assertTrue(collectorLogs.contains("expected content"));
```

**Why Docker log verification?**
- Tests the **real export pipeline** (not mocked)
- Validates OTLP JSON format correctness
- Ensures collector can parse exported data
- Catches serialization issues that mocks would hide

**Trade-offs**:
- ✅ High confidence in end-to-end functionality
- ✅ Tests real-world scenarios
- ❌ Slower execution (~2-3 minutes)
- ❌ External dependency (Docker, collector)
- ❌ Potential flakiness (timing, log format changes)

**Expected output** in collector logs:
```
Resource attributes:
     -> service.name: Str(http-db-java-tracer)  ✓
     -> service.version: Str(1.0.0)

LogRecord #0
Body: Str(Database query executed: SELECT (rows: 3))
Attributes:
     -> db.system: Str(mysql)
     -> db.statement: Str(SELECT * FROM users)
     -> db.rows.count: Int(3)
     -> http.request.body: Str({"name":"John","email":"<REDACTED_EMAIL>"})
     -> http.response.body: Str({"id":1,"name":"John",...})
```

## Common Pitfalls

**Don't**:
- Use instance methods in ByteBuddy Advice classes (must be static)
- Use `Resource.getDefault()` in OtelLogRecordBuilder (breaks service.name)
- Catch broad exceptions in interceptors without rethrowing (hides bugs)
- Forget to test with actual ORM frameworks (JPA, MyBatis) - they generate complex SQL

**Do**:
- Always pass Resource parameter to OtelLogRecordBuilder
- Test with OpenTelemetry Collector running
- Verify JSON format is readable with tcpdump or collector logs
- Handle LOB data types gracefully (mark as `[LOB Data]`)
- Use VirtualField pattern for any per-ResultSet state

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Java | 8+ | Minimum compatibility |
| Gradle | 8.5 | Build system (use wrapper) |
| ByteBuddy | 1.14.10 | Bytecode instrumentation |
| OpenTelemetry SDK | 1.42.1 | Telemetry framework |
| Jackson | 2.15.2 | JSON serialization |
| OkHttp | 4.12.0 | HTTP client for OTLP |
| SLF4J + Logback | 1.7.36 / 1.4.11 | Logging |

## Additional Resources

- **README.md** - User-facing documentation and configuration reference
- **AGENTS.md** - Coding style, commit guidelines, module organization
- **docs/FIX_SUMMARY.md** - Recent fixes and improvements (2025-10-11)
- **docs/OTLP_JSON_IMPLEMENTATION.md** - JSON format implementation details
- **docs/OPENTELEMETRY.md** - OpenTelemetry integration guide

## Active Technologies
- Java 8+ (maintaining compatibility with existing db-monitor agent codebase) (004-http-trace-agent)
- N/A (agent exports telemetry; no persistent storage) (004-http-trace-agent)
- Java 8+ (maintaining compatibility with existing db-monitor agent codebase) + ByteBuddy 1.14.10, OpenTelemetry SDK 1.42.1, Jackson 2.15.2, Servlet 3.0+ API (005-http-body-capture)
- Java 8+ (maintaining compatibility with existing db-monitor agent codebase) + ByteBuddy 1.14.10, Servlet 3.0 API (javax.servlet.*), OpenTelemetry SDK 1.42.1 (006-servlet30-body-capture)

## Recent Changes
- 004-http-trace-agent: Added Java 8+ (maintaining compatibility with existing db-monitor agent codebase)