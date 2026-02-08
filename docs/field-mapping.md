# Field Mapping Guide

When using `epicenv secrets get` with other commands, you may need to transform or map fields to match the expected format. Since `epicenv secrets get` outputs JSON to stdout, you can use standard Unix tools like `jq` to transform the data.

## Why Field Mapping?

Common scenarios where field mapping is useful:

- Your 1Password item uses different field names (e.g., `e-mail` instead of `email`)
- You want to use one field for multiple purposes (e.g., `username` as both username and email)
- You need to transform values (e.g., lowercase emails, add domain suffixes)
- You have nested or complex data structures

## Basic Examples

### Use username as email

If your 1Password item only has a `username` field but you need an `email`:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  epicenv create-superuser
```

This adds an `email` field with the same value as `username`.

### Rename a field

If your 1Password item has `e-mail` but the command expects `email`:

```bash
epicenv secrets get op://vault/admin --fields username,e-mail,password | \
  jq '{username, email: .["e-mail"], password}' | \
  epicenv create-superuser
```

**Note:** Use bracket notation `["e-mail"]` for field names with special characters.

### Transform to lowercase

Ensure email addresses are lowercase:

```bash
epicenv secrets get op://vault/admin --fields username,email,password | \
  jq '.email |= ascii_downcase' | \
  epicenv create-superuser
```

### Add domain to username

Create an email by appending a domain to the username:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '{username, email: (.username + "@example.com"), password}' | \
  epicenv create-superuser
```

## Advanced Examples

### Multiple transformations

Combine multiple transformations in one `jq` expression:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '{
    username: .username,
    email: (.username | ascii_downcase | . + "@example.com"),
    password
  }' | \
  epicenv create-superuser
```

### Conditional mapping

Use `username` as `email` only if it contains an `@` symbol:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '{
    username,
    email: (if .username | contains("@") then .username else (.username + "@example.com") end),
    password
  }' | \
  epicenv create-superuser
```

### Extract nested fields

If your 1Password item stores credentials as a JSON string:

```bash
epicenv secrets get op://vault/admin --fields admin_credentials | \
  jq '.admin_credentials | fromjson' | \
  epicenv create-superuser
```

### Map multiple fields with different names

```bash
epicenv secrets get op://vault/admin --fields user_name,user_email,user_pass | \
  jq '{
    username: .user_name,
    email: .user_email,
    password: .user_pass
  }' | \
  epicenv create-superuser
```

## Working with Environment Variables

You can also transform environment variables before passing them:

```bash
# Transform username to email using jq
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_PASSWORD=secret

echo "{\"username\":\"$DJANGO_SUPERUSER_USERNAME\",\"password\":\"$DJANGO_SUPERUSER_PASSWORD\"}" | \
  jq '. + {email: (.username + "@example.com")}' | \
  epicenv create-superuser
```

## Docker Compose Integration

Field mapping works seamlessly with Docker containers:

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  docker compose exec -T web epicenv create-superuser
```

**Important:** Use the `-T` flag with `docker compose exec` to disable TTY allocation and allow stdin to pass through.

## jq Quick Reference

### Common jq Patterns

| Task | jq Expression | Example |
|------|---------------|---------|
| Add field | `. + {key: value}` | `. + {email: .username}` |
| Rename field | `{new: .old}` | `{email: .["e-mail"]}` |
| Transform value | `.field \|= expression` | `.email \|= ascii_downcase` |
| Concatenate | `(.field1 + .field2)` | `(.username + "@example.com")` |
| Conditional | `if condition then value else value end` | `if .username \| contains("@") then .username else .username + "@example.com" end` |
| Parse JSON string | `.field \| fromjson` | `.credentials \| fromjson` |
| Select fields | `{field1, field2}` | `{username, email, password}` |

### Learning jq

- Official tutorial: https://jqlang.github.io/jq/tutorial/
- Interactive playground: https://jqplay.org/
- Manual: https://jqlang.github.io/jq/manual/

## Alternative Approaches

While `jq` is the recommended approach for field mapping, you can also:

### 1. Use Python for complex transformations

```bash
epicenv secrets get op://vault/admin --fields username,password | \
  python -c '
import json, sys
data = json.load(sys.stdin)
data["email"] = data["username"].lower() + "@example.com"
print(json.dumps(data))
' | \
  epicenv create-superuser
```

### 2. Fetch fields with correct names

If possible, update your 1Password item to use the expected field names:
- Use `username`, `email`, `password` as field names
- This avoids the need for any transformation

### 3. Create wrapper scripts

For frequently used transformations, create a shell script:

```bash
#!/bin/bash
# create-admin.sh

epicenv secrets get "$1" --fields username,password | \
  jq '. + {email: .username}' | \
  epicenv create-superuser
```

Usage:
```bash
./create-admin.sh op://vault/admin
```

## Best Practices

1. **Keep transformations simple** - Complex jq expressions are hard to debug
2. **Test transformations** - Pipe to `jq` alone first to verify output before piping to `create-superuser`
3. **Document custom mappings** - Add comments to scripts explaining non-obvious transformations
4. **Use consistent field names** - When possible, standardize field names in your secrets manager
5. **Handle missing fields** - Use jq's `// "default"` operator to provide fallbacks

## Example: Testing Transformations

Before piping to `create-superuser`, test your jq transformation:

```bash
# Test the transformation first
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}'

# Output (verify this looks correct):
# {
#   "username": "admin",
#   "password": "secret123",
#   "email": "admin"
# }

# If correct, add the final command
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  epicenv create-superuser
```

## Troubleshooting

### Error: "jq: command not found"

Install jq:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Fedora/RHEL
sudo dnf install jq

# Arch
sudo pacman -S jq
```

### Error: "Missing required fields in JSON"

Verify your jq transformation outputs all required fields (`username`, `email`, `password`):

```bash
# Debug by checking the output
epicenv secrets get op://vault/admin --fields username,password | \
  jq '. + {email: .username}' | \
  jq 'keys'  # Should show: ["email", "password", "username"]
```

### Special characters in field names

Use bracket notation for field names with hyphens, spaces, or other special characters:

```bash
jq '{username, email: .["e-mail"], password: .["user password"]}'
```
