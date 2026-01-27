# 1Password Integration

epicenv includes a built-in initializer that fetches secrets from 1Password CLI during `.env` file generation.

## Quick Start

```toml
[tool.epicenv.variables]
STRIPE_API_KEY = {
    type = "str",
    required = true,
    help_text = "Stripe API key for payments",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/Stripe/api_key"]
}
```

Run `epicenv create` and the secret will be fetched from your 1Password vault.

## Prerequisites

1. **Install 1Password CLI**: https://developer.1password.com/docs/cli/get-started/
2. **Sign in**: Run `op signin` and follow the prompts

Verify installation:
```bash
op --version
```

## Configuration Options

### Basic Usage

```toml
STRIPE_API_KEY = {
    type = "str",
    required = true,
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/Stripe/api_key"]
}
```

### With Custom Fallback

If 1Password is unavailable, use a custom fallback value instead of the auto-generated placeholder:

```toml
DATABASE_PASSWORD = {
    type = "str",
    required = true,
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/Database/password"],
    kwargs = { fallback = "local_dev_password" }
}
```

### Silent Mode

Suppress warnings when 1Password is unavailable:

```toml
OPTIONAL_SECRET = {
    type = "str",
    default = "",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Development/Optional/secret"],
    kwargs = { silent = true, fallback = "" }
}
```

## Reference Format

The reference string follows 1Password's [secret reference format](https://developer.1password.com/docs/cli/secret-references/):

| Format | Example |
|--------|---------|
| Basic | `op://vault/item/field` |
| With section | `op://vault/item/section/field` |

Examples:
- `op://Production/AWS/access_key_id`
- `op://Development/API Keys/stripe/production_key`
- `op://Personal/Database/postgres/password`

## Behavior

| Condition | Result |
|-----------|--------|
| 1Password available | Secret fetched from vault |
| 1Password not installed | Uses fallback (or `[Enter VARIABLE_NAME]` placeholder) |
| Not signed in | Uses fallback with warning |
| Secret not found | Uses fallback with error message |

## Troubleshooting

### "1Password CLI not installed"

**Solution:** Install the CLI from https://developer.1password.com/docs/cli/get-started/

Verify with:
```bash
op --version
```

### "Not signed in to 1Password CLI"

**Solution:** Sign in to 1Password:
```bash
op signin
```

Follow the prompts to authenticate. You may need to enter your master password or use biometric authentication.

### "Failed to read secret: vault not found"

**Possible causes:**
- Vault name is misspelled
- You don't have access to the vault

**Solution:** List your available vaults:
```bash
op vault list
```

### "Failed to read secret: item not found"

**Possible causes:**
- Item name is misspelled
- Item doesn't exist in the specified vault

**Solution:** Search for the item:
```bash
op item list --vault "Production"
```

### "Timeout reading from 1Password"

**Possible causes:**
- Network connectivity issues
- 1Password service is slow

**Solution:**
1. Check your internet connection
2. Try signing in again: `op signin`
3. Increase timeout if available

### Fallback Values Appearing in .env

If you see `[Enter VARIABLE_NAME]` in your generated `.env` file, it means:

1. 1Password CLI is not installed, OR
2. You're not signed in, OR
3. The secret reference is incorrect

Check the terminal output from `epicenv create` for specific warnings about what went wrong.

## Best Practices

1. **Use vaults to organize secrets** - Separate production, staging, and development secrets
2. **Set fallbacks for local development** - Use `kwargs = { fallback = "local_value" }` for secrets that are only needed in production
3. **Use silent mode for optional secrets** - Add `silent = true` for secrets that might not exist in all environments
4. **Document reference paths** - Use `help_text` to document where the secret comes from

## Example: Complete Configuration

```toml
[tool.epicenv.variables]
# Production secrets from 1Password
STRIPE_SECRET_KEY = {
    type = "str",
    required = true,
    help_text = "Stripe secret key (op://Production/Stripe/secret_key)",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/Stripe/secret_key"],
    kwargs = { fallback = "sk_test_placeholder" }
}

SENDGRID_API_KEY = {
    type = "str",
    required = true,
    help_text = "SendGrid API key for email",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/SendGrid/api_key"]
}

# Optional integration - silent if not available
SENTRY_DSN = {
    type = "str",
    default = "",
    help_text = "Sentry DSN for error tracking",
    initial_func = "epicenv.initializers.onepassword",
    args = ["op://Production/Sentry/dsn"],
    kwargs = { silent = true, fallback = "" }
}
```
