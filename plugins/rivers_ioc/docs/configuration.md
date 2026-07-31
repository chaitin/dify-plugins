# Configuration and troubleshooting

The plugin sends the configured token in the `X-CA-Token` header only to
`https://intelligence.rivers.chaitin.cn`. Queries have explicit connection and response timeouts.

- Authentication errors: verify the token and its threat-intelligence permission.
- Rate limiting: wait before retrying or review the service quota.
- Timeout/service unavailable: retry after checking Rivers service availability.
- Invalid input: provide one literal IPv4 or IPv6 address, not a hostname or CIDR.

Tokens and complete upstream error bodies are never emitted in plugin error messages.
