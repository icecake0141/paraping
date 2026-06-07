# ParaPing API Documentation

## Module Layout

ParaPing is organized around the installed CLI entrypoint and runtime package.

### Entrypoints

- `paraping.cli`: command-line parsing, runtime setup, event loop, host reloads, and interactive actions.
- `paraping.__main__`: module execution entrypoint for `python -m paraping`.

### Runtime

- `paraping.runtime.engine`: monitor state and event application.
- `paraping.runtime.domain`: runtime data objects.
- `paraping.runtime.history`: bounded history snapshots.
- `paraping.runtime.render_state`: live/history render-source selection.
- `paraping.runtime.render_projection`: projection from runtime state to UI render buffers.
- `paraping.runtime.hosts`: host-file parsing and host-info construction.
- `paraping.runtime.scheduler`: ping scheduling.
- `paraping.runtime.sequence_tracker`: ICMP sequence tracking.
- `paraping.runtime.rate_limit`: global ping-rate validation.
- `paraping.runtime.term_size` and `paraping.runtime.paging`: terminal sizing and history paging helpers.

### UI And Operators

- `paraping.ui_render`: terminal rendering, layout, panels, graphs, and ANSI output.
- `paraping.input_keys`: raw key parsing.
- `paraping.keymap`: interactive key bindings.
- `paraping.stats`: summary and grouping metrics.
- `paraping.config`: config loading and runtime setting persistence.

### Network And Helper Integration

- `paraping.pinger`: worker ping flow and rDNS worker behavior.
- `paraping.ping_wrapper`: subprocess wrapper for the native ICMP helper.
- `paraping.network_rdns`: reverse DNS helpers.
- `paraping.network_asn`: Team Cymru ASN lookup.
- `src/native/ping_helper.c`: privileged ICMP helper.

See [runtime_architecture.md](../runtime_architecture.md) for ownership and test routes.
See [scheduler.md](scheduler.md) and [ping_helper.md](../ping_helper.md) for focused references.
