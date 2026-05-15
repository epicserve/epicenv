# Field Mapping Guide

`epicenv secrets get` emits JSON on stdout, so when the consuming command expects different field names you can transform the data with [`jq`](https://jqlang.github.io/jq/) before piping it on.

## When you need this

- Your 1Password item uses field names that don't match the consumer (`e-mail` vs `email`)
- You want to derive one field from another (email = `username + "@example.com"`)
- The consumer needs a subset/superset of what the item stores
- You need to normalize values (lowercase, trim, etc.)

## Core patterns

**Add a field derived from another.** Use `username` as both username and email:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  epicenv create-superuser
```

**Rename a field with special characters.** 1Password stores `e-mail` but the consumer expects `email`:

```bash
epicenv secrets get op://vault/admin --fields username,e-mail,password | \
  jq '{username, email: .["e-mail"], password}' | \
  epicenv create-superuser
```

**Transform values.** Lowercase the email, or append a domain:

```bash
# Lowercase
... | jq '.email |= ascii_downcase' | ...

# Append domain to username to build an email
... | jq '{username, email: (.username + "@example.com"), password}' | ...
```

**Map multiple fields with different names** into the expected schema:

```bash
epicenv secrets get op://vault/admin --fields user_name,user_email,user_pass | \
  jq '{username: .user_name, email: .user_email, password: .user_pass}' | \
  epicenv create-superuser
```

## Docker Compose

`docker compose exec` swallows stdin by default — use `-T` to pass it through:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  docker compose exec -T web epicenv create-superuser
```

## Tips

- **Test the transform alone first.** Pipe `epicenv secrets get … | jq '<expr>'` and eyeball the output before adding the downstream consumer.
- **Standardize field names where you can.** If you control the 1Password item, naming fields `username` / `email` / `password` avoids needing any mapping at all.
- For anything beyond simple field-shape manipulation, see the [jq manual](https://jqlang.github.io/jq/manual/) or the [jq playground](https://jqplay.org/).

## Troubleshooting

**"Missing required fields in JSON" from `epicenv create-superuser`:** check that your `jq` expression emits all of `username`, `email`, `password`:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  jq 'keys'   # should print ["email", "password", "username"]
```

**`jq: command not found`:** install with `brew install jq` / `apt-get install jq` / `dnf install jq` / `pacman -S jq`.
