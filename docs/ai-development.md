# AI Development and Deployment

TODO

---

## Checking your PyPi Libraries

It is recommended that you frequently check the set of your PyPi
library dependencies, per your pyproject.toml file, to check for
outdated versions and known security issues.

The **uv** Python project manager offers excellent support for this
with the **uv audit** and **uv pip list --outdated** commands.

You can read more about uv here: https://docs.astral.sh/uv/

### Check for Security Issues

**uv audit** scans your project's dependencies for known security vulnerabilities
and deprecated statuses.  The output shown below shows that there is an issue
with 1.44.0 of library opentelemetry-api.  Therefore, you should upgrade it to
a newer version.  See https://pypi.org/project/opentelemetry-api/

```
cd app/

uv audit

warning: `uv audit` is experimental and may change without warning. Pass `--preview-features audit-command` to disable this warning.
Resolved 94 packages in 287ms
Found 1 known vulnerability and no adverse project statuses in 93 packages

Vulnerabilities:

opentelemetry-api 1.44.0 has 1 known vulnerability:

- GHSA-xcq7-p3pf-p88h: OpenTelemetry Python: Unbounded tracestate parsing in opentelemetry-api

  Fixed in: 1.45.1

  Advisory information: https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-xcq7-p3pf-p88h
```

Clean output looks like this:

```
uv audit
warning: `uv audit` is experimental and may change without warning. Pass `--preview-features audit-command` to disable this warning.
Resolved 94 packages in 4ms
Found no known vulnerabilities and no adverse project statuses in 93 packages
```

### Check for Newer Library Versions

```
uv pip list --outdated

Package                        Version    Latest      Type
------------------------------ ---------- ----------- -----
agent-framework-core           1.22.0     1.24.0      wheel
agent-framework-foundry        1.15.0     1.16.0      wheel
agent-framework-openai         1.17.0     1.18.0      wheel
agent-framework-orchestrations 1.3.2      1.4.1       wheel
...
```

You may wish to **surgically/manually** upgrade specific libraries per this output.

Alternatively, you can upgrade all of your libraries as described in the next section.

### Mass-update your Library Versions

The **uv sync --upgrade** can do this.

```
cd wrangling/

uv sync --upgrade
...

uv pip list --outdated
(no output lines as all libraries have been upgraded to current version)
```

Be sure to retest your application after upgrading your libraries.

### Recreating your Python Virtual Environment

This is one way to do it.  uv will recreate the venv when you run any python program.

```
cd app/

rm -rf .venv 

uv run main-xxx.py
```
