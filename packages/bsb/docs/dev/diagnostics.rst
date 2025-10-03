Diagnostics
===========

The BSB is instrumented with OpenTelemetry for observability and diagnostics purposes. This guide explains how to set up
tracing and profiling for development and debugging.

Jaeger Setup
------------

To collect and visualize traces, you can use Jaeger. The easiest way to set up Jaeger is using Docker:

.. code-block:: bash

    docker run -d \
        --name jaeger \
        -p 9411:9411 \
        -p 4318:4318 \
        -p 4317:4317 \
        -p 16686:16686 \
        -p 5778:5778 \
        cr.jaegertracing.io/jaegertracing/jaeger:2.9.0

OpenTelemetry Instrumentation
-----------------------------

The BSB supports OpenTelemetry instrumentation through the `opentelemetry-instrument` command-line tool, which provides zero-code
instrumentation capabilities. For detailed configuration options, refer to the `OpenTelemetry Python Documentation
<https://opentelemetry.io/docs/instrumentation/python/automatic/>`_.

The following command demonstrates how to enable tracing and metrics:

.. code-block:: bash

    opentelemetry-instrument \
        --traces_exporter console,otlp \
        --metrics_exporter console \
        --exporter_otlp_endpoint 0.0.0.0:4317 \
        python -m bsb compile --clear

Command options explained:
- ``--traces_exporter console,otlp``: Configures trace export to both console (for immediate debugging) and OTLP protocol
- ``--metrics_exporter console``: Enables metrics output to console for monitoring
- ``--exporter_otlp_endpoint 0.0.0.0:4317``: Specifies the OTLP endpoint (default Jaeger collector port)
- Additional options can be found in the OpenTelemetry Python documentation

The instrumentation will:
- Export traces to both console and OTLP endpoint for analysis
- Export metrics to console for performance monitoring
- Send OTLP data to the configured Jaeger instance (or other compatible backends)
- Automatically instrument the BSB compilation process with minimal overhead

Profiling
---------

The BSB includes a profiling module that can be enabled through various methods:

1. Command line flag:

.. code-block:: bash

    python -m bsb compile --profiling

2. Environment variable:

.. code-block:: bash

    export BSB_PROFILING=1
    python -m bsb compile

3. Configuration option in code:

.. code-block:: python

    from bsb import options
    options.profiling = True

The profiling results will be collected and can be analyzed to identify performance bottlenecks and optimization opportunities.
